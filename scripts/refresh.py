#!/usr/bin/env python3
"""Re-check every deal/dupe price + stock at the retailer, drop dead ones, write data/deals.json.
Source: Perfumania public Shopify product JSON (https://www.perfumania.com/products/<handle>.json).
Free, no API key. Run daily (cron / GitHub Actions)."""
import json, time, urllib.request, urllib.error, datetime, os, sys
import links
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA="Mozilla/5.0 (compatible; ScentDealsDailyBot/1.0; +https://scentdealsdaily.com)"
STORE="https://www.perfumania.com"
PAUSE=float(os.environ.get("REFRESH_PAUSE","1.2"))  # seconds between products; keeps us under Perfumania's rate limit
FAIL={"transient":0,"total":0}
def fetch(url, tries=6):
    """GET JSON with backoff. Perfumania rate-limits bursts (HTTP 429) from CI runners, so retry
    with Retry-After / exponential backoff instead of silently dropping live deals.
    Tracking and internal redirect URLs are never requested; a plain retailer URL is used instead."""
    safe=links.safe_request_url(url)
    if not safe:
        print("  ! refused affiliate tracking url (not requested)", file=sys.stderr)
        return None
    url=safe
    FAIL["total"]+=1
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==404: print("  ! 404",url,file=sys.stderr); return None
            if e.code in (429,500,502,503,504) and i<tries-1:
                ra=e.headers.get("Retry-After"); w=float(ra) if ra and ra.replace(".","",1).isdigit() else min(60,4*2**i)
                print(f"  ~ {e.code} {url.rsplit('/',1)[-1]} retry in {w:.0f}s",file=sys.stderr); time.sleep(w); continue
            print("  !",url,e,file=sys.stderr); FAIL["transient"]+=1; return None
        except Exception as e:
            if i<tries-1: time.sleep(min(60,4*2**i)); continue
            print("  !",url,e,file=sys.stderr); FAIL["transient"]+=1; return None
def get(handle):
    d=fetch(f"{STORE}/products/{handle}.json"); return d["product"] if d else None
def best_variant(p, require_discount=True):
    vs=[v for v in p["variants"] if v.get("available",True) is not False and "tester" not in (v["title"]+p["title"]).lower()]
    out=[]
    for v in vs:
        pr=float(v["price"]); c=float(v["compare_at_price"] or 0)
        if require_discount and c<=pr: continue
        out.append((1-pr/c if c>pr else 0, v, pr, c))
    return max(out,key=lambda x:x[0]) if out else None
def _plain(html_body):
    import html as _html
    import re as _re
    text=_re.sub(r"<[^>]+>"," ", html_body or "")
    text=_html.unescape(text)
    return _re.sub(r"\s+"," ", text).strip()
def _cut_contents(fragment):
    """Stop at a sentence end. Keep decimals (0.25) and the abbreviation oz."""
    out=[]
    for i,ch in enumerate(fragment):
        if len(out)>=420:
            break
        if ch==".":
            prev=fragment[i-1] if i else ""
            if prev.isdigit() or fragment[max(0,i-2):i].lower()=="oz":
                out.append(ch)
                continue
            break
        out.append(ch)
    return "".join(out).strip(" .,;")
def contents_from(html_body):
    """Piece list copied from the retailer description. Empty when the page does not list pieces."""
    import re as _re
    items=[]
    for raw in _re.findall(r"<li>(.*?)</li>", html_body or "", _re.I|_re.S):
        line=_plain(raw).strip(" .,;")
        if line and len(line)<=160:
            items.append(line)
    if len(items)>=2 and not any(_re.search(r"\bnotes?\b", line, _re.I) for line in items):
        return "; ".join(items)
    text=_plain(html_body)
    for pat in (r"gift set includes\b", r"\d+\s*-?\s*(?:pc|piece)\s+gift set\b"):
        m=_re.search(pat, text, _re.I)
        if not m:
            continue
        cut=_cut_contents(text[m.start():])
        if len(cut)>=12:
            return cut
    return ""
def _oz_in(title):
    import re as _re
    m=_re.search(r"([0-9]*\.?[0-9]+)\s*oz", title or "", _re.I)
    return float(m.group(1)) if m else None
def collect_gifts(cfg, now, avail_fn):
    """In-stock minis and boxed sets from config gift_catalog. Prices come from the product JSON.

    Minis are one sealed 0.3–1.0 oz spray. Sets must be gift sets on the retailer page.
    No 15% rule: these pages list a checked price, not only a deep discount.
    """
    import re as _re
    gifts=[]
    for item in cfg.get("gift_catalog") or []:
        h=item.get("handle")
        kind=item.get("kind")
        if not h or kind not in ("mini","set"):
            continue
        p=get(h); time.sleep(PAUSE)
        if not p:
            print("  ! gift miss", h, file=sys.stderr); continue
        stock=avail_fn(h) or {}
        want=item.get("size")
        want_f=float(want) if want not in (None,"") else None
        cands=[]
        for v in p.get("variants") or []:
            title=v.get("title") or ""
            blob=(title+" "+(p.get("title") or "")).lower()
            if any(x in blob for x in ("tester","unboxed","decant")):
                continue
            if stock.get(v["id"]) is not True:
                continue
            if want_f is not None:
                got=_oz_in(title)
                if got is None or abs(got-want_f)>0.02:
                    continue
            try:
                pr=float(v["price"])
            except (TypeError, ValueError):
                continue
            if pr<=0:
                continue
            try:
                compare=float(v.get("compare_at_price") or 0)
            except (TypeError, ValueError):
                compare=0
            cands.append((pr, compare, v))
        if not cands:
            print("  ! gift out of stock or size miss", h, file=sys.stderr); continue
        pr, compare, v=min(cands, key=lambda row: row[0])
        title_blob=" ".join((p.get("title") or "", p.get("product_type") or "", p.get("handle") or "")).lower()
        if kind=="set":
            set_ok=(p.get("product_type") or "").lower()=="gift set" or any(s in title_blob for s in ("gift set","gift-set","coffret","discovery set","mini set")) or _re.search(r"\b\d+\s*-?\s*(pc|piece|pcs)\b", title_blob)
            if not set_ok:
                print("  ! gift not a set", h, file=sys.stderr); continue
        else:
            got=_oz_in(v.get("title") or "")
            if got is None or got<0.3 or got>1.05:
                print("  ! gift mini size", h, got, file=sys.stderr); continue
            if "gift set" in (p.get("title") or "").lower() or "gift set" in (p.get("product_type") or "").lower():
                print("  ! gift mini is a set", h, file=sys.stderr); continue
        row={"id":h,"brand":p.get("vendor") or "","name":p.get("title") or "","size":(v.get("title") or "").strip(),
             "type":p.get("product_type") or "","gender":gift_gender(p),"price":round(pr,2),
             "pct_off":round((1-pr/compare)*100) if compare>pr else 0,
             "retailer":"Perfumania","url":f"{STORE}/products/{h}?variant={v['id']}",
             "image":(p.get("image") or {}).get("src"),"checked":now,"in_stock":True,"kind":kind}
        if compare>pr:
            row["was"]=round(compare,2)
        if kind=="set":
            contents=contents_from(p.get("body_html") or "")
            if contents:
                row["contents"]=contents
        gifts.append(row)
    return gifts
def gift_gender(p):
    """Read GENDER_Men / GENDER_Women tags. Titles of sets often omit who the set is for."""
    import re as _re
    tags=p.get("tags") or []
    if isinstance(tags, str):
        tags=[t.strip() for t in tags.split(",")]
    for tag in tags:
        tl=tag.lower().replace("_"," ")
        if "gender" not in tl:
            continue
        if "women" in tl:
            return "women"
        if _re.search(r"\bmen\b", tl):
            return "men"
        if "unisex" in tl:
            return "unisex"
    return gender(p)
def gender(p):
    t=(p["title"]+" "+p.get("handle","").replace("-"," ")+" "+" ".join(p.get("tags",[]) if isinstance(p.get("tags"),list) else [p.get("tags","")])).lower()  # handle catches e.g. "ck-one-...-unisex-fragrance" tagged GENDER_Women
    if "unisex" in t: return "unisex"
    if "cologne" in t or " men" in t or "for men" in t: return "men"
    if "perfume" in t or "women" in t: return "women"
    return "unisex"
def main():
    cfg=json.load(open(f"{ROOT}/data/config.json"))
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # stock status needs storefront availability; products/<h>.json omits 'available', so use .js endpoint
    def avail(handle):
        d=fetch(f"{STORE}/products/{handle}.js")
        return {v["id"]:v["available"] for v in d["variants"]} if d else {}
    deals=[]; dropped=[]
    for h in cfg["deals"]:
        p=get(h); time.sleep(PAUSE)
        if not p: dropped.append(h); continue
        a=avail(h)
        for v in p["variants"]: v["available"]=a.get(v["id"],False)
        b=best_variant(p)
        if not b or b[0]<0.15: dropped.append(h); continue
        pct,v,pr,c=b
        deals.append({"id":h,"brand":p["vendor"],"name":p["title"],"size":v["title"].strip(),"type":p.get("product_type",""),
          "gender":gender(p),"price":round(pr,2),"was":round(c,2),"pct_off":round(pct*100),
          "retailer":"Perfumania","url":f"{STORE}/products/{h}?variant={v['id']}",
          "image":(p.get("image") or {}).get("src"),"checked":now,"in_stock":True})
    # price-comparison deals: Perfumania >=15% below another authorized retailer (Muse.ai sources; eBay/marketplace excluded upstream)
    import re
    for cd in cfg.get("compare_deals",[]):
        h=cd["handle"]
        if any(x["id"]==h for x in deals): continue
        p=get(h); time.sleep(PAUSE)
        if not p: dropped.append(h); continue
        a=avail(h)
        vs=[v for v in p["variants"] if a.get(v["id"]) and "tester" not in v["title"].lower() and re.match(r"\s*"+re.escape(cd["size"])+r"\b",v["title"])]
        if not vs: dropped.append(h); continue
        v=vs[0]; pr=float(v["price"]); ref=max(cd["comps"],key=lambda c:c["price"])
        if pr>ref["price"]*0.85: dropped.append(h+" (<15% below "+ref["retailer"]+")"); continue
        comps=[{"retailer":"Perfumania","price":pr,"url":f"{STORE}/products/{h}?variant={v['id']}","checked":now}]+cd["comps"]
        deals.append({"id":h,"brand":p["vendor"],"name":p["title"],"size":v["title"].strip(),"type":p.get("product_type",""),
          "gender":gender(p),"price":round(pr,2),"was":ref["price"],"was_label":ref["retailer"],"pct_off":round((1-pr/ref["price"])*100),
          "retailer":"Perfumania","url":comps[0]["url"],"image":(p.get("image") or {}).get("src"),"checked":now,"in_stock":True,"comps":comps})
    # FragranceShop is a second CJ retailer. A miss leaves the deal Perfumania-only.
    # FragranceNet is Rakuten. A blocked fetch keeps the last checked FragranceNet price.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fragranceshop import attach as attach_fragranceshop
    attach_fragranceshop(deals)
    from fragrancenet import attach as attach_fragrancenet, restore as restore_fragrancenet
    fn=attach_fragrancenet(deals, now)
    if fn.get("blocked"):
        try:
            prev_fn=json.load(open(f"{ROOT}/data/deals.json"))
        except Exception:
            prev_fn={}
        restore_fragrancenet(deals, prev_fn.get("deals") or [], fn["blocked"])
    # only true 15%+ discounts get published, whichever store ends up selling it
    for d in [d for d in deals if (d.get("pct_off") or 0)<15]:
        deals.remove(d); dropped.append(d["id"]+f" (only {d.get('pct_off')}% off after store merge)")
    deals.sort(key=lambda d:-d["pct_off"])
    dupes=[]
    for d in cfg["dupes"]:
        d=dict(d); d["price"]=None; d["url"]=None; d["checked"]=None
        if d.get("handle"):
            p=get(d["handle"]); time.sleep(PAUSE)
            if p:
                a=avail(d["handle"])
                for v in p["variants"]: v["available"]=a.get(v["id"],False)
                b=best_variant(p,require_discount=False)
                if b:
                    _,v,pr,c=b
                    d.update(price=round(pr,2),was=round(c,2) if c>pr else None,size=v["title"].strip(),retailer="Perfumania",
                             url=f"{STORE}/products/{d['handle']}?variant={v['id']}",image=(p.get("image") or {}).get("src"),checked=now)
        if d.get("comps") and d["price"]: d["comps"]=[{"retailer":"Perfumania","price":d["price"],"url":d["url"],"checked":now}]+d["comps"]
        dupes.append(d)
    attach_fragranceshop([], dupes)
    out=f"{ROOT}/data/deals.json"
    # Degraded-run guard: if many fetches still failed after retries (rate limit / outage), don't publish a
    # half-empty site. Keep the last fully verified file (its own 'updated' time stays visible) unless it's >48h old.
    if FAIL["total"] and FAIL["transient"]/FAIL["total"]>0.2 and os.path.exists(out):
        try:
            prev=json.load(open(out)); age=datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.strptime(prev["updated"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except Exception: age=None
        if age is not None and age<datetime.timedelta(hours=48):
            print(f"DEGRADED refresh: {FAIL['transient']}/{FAIL['total']} fetches failed; keeping previous deals.json from {prev['updated']}",file=sys.stderr)
            return
    # A FragranceShop outage should not wipe prices we already checked today.
    import fragranceshop as _fs
    st=_fs.STATS
    if st["total"] and st["transient"]/st["total"]>0.5 and os.path.exists(out):
        try:
            prev=json.load(open(out))
            age=datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.strptime(prev["updated"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        except Exception:
            prev, age=None, None
        if prev and age is not None and age<datetime.timedelta(hours=48):
            def _restore(rows, olds, key):
                old={x.get(key):x for x in olds}
                for row in rows:
                    src=old.get(row.get(key))
                    if not src or not src.get("fs") or row.get("fs"): continue
                    if (src.get("size") or "").strip()!= (row.get("size") or "").strip(): continue
                    _fs._apply(row, {"retailer":"FragranceShop","price":src["fs"]["price"],"was":src["fs"].get("was"),"url":src["fs"]["url"],"matched":src["fs"].get("name"),"variation":src["fs"].get("variation")})
            _restore(deals, prev.get("deals") or [], "id")
            _restore(dupes, prev.get("dupes") or [], "dupe")
            print(f"fragranceshop fetch degraded ({st['transient']}/{st['total']}); kept same-day FragranceShop prices", file=sys.stderr)
    deals=[d for d in deals if (d.get("pct_off") or 0)>=15]
    deals.sort(key=lambda d:-d["pct_off"])
    # Gift pages read this list. A failed pass keeps the previous list so a blip
    # does not empty stocking and gift-set pages that were already checked.
    gifts=collect_gifts(cfg, now, avail) if cfg.get("gift_catalog") else []
    if cfg.get("gift_catalog") and not gifts:
        try:
            prev_gifts=(json.load(open(out)).get("gifts") or [])
        except Exception:
            prev_gifts=[]
        if prev_gifts:
            gifts=prev_gifts
            print(f"gift catalog fetch returned nothing; kept {len(gifts)} previous gift rows", file=sys.stderr)
    json.dump({"updated":now,"deals":deals,"dupes":dupes,"dropped":dropped,"gifts":gifts},open(out,"w"),indent=1)
    print(f"{len(deals)} live deals, {len(gifts)} gift rows, {len(dropped)} dropped {dropped}, {sum(1 for d in dupes if d['price'])}/{len(dupes)} dupes priced, {FAIL['transient']}/{FAIL['total']} fetch failures")
if __name__=="__main__": main()
