#!/usr/bin/env python3
"""Re-check every deal/dupe price + stock at the retailer, drop dead ones, write data/deals.json.
Source: Perfumania public Shopify product JSON (https://www.perfumania.com/products/<handle>.json).
Free, no API key. Run daily (cron / GitHub Actions)."""
import json, time, urllib.request, datetime, os, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA="Mozilla/5.0 (compatible; ScentDealsDailyBot/1.0; +https://scentdealsdaily.com)"
STORE="https://www.perfumania.com"
def get(handle):
    req=urllib.request.Request(f"{STORE}/products/{handle}.json",headers={"User-Agent":UA})
    try:
        with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)["product"]
    except Exception as e:
        print("  !",handle,e,file=sys.stderr); return None
def best_variant(p, require_discount=True):
    vs=[v for v in p["variants"] if v.get("available",True) is not False and "tester" not in (v["title"]+p["title"]).lower()]
    out=[]
    for v in vs:
        pr=float(v["price"]); c=float(v["compare_at_price"] or 0)
        if require_discount and c<=pr: continue
        out.append((1-pr/c if c>pr else 0, v, pr, c))
    return max(out,key=lambda x:x[0]) if out else None
def gender(p):
    t=(p["title"]+" "+" ".join(p.get("tags",[]) if isinstance(p.get("tags"),list) else [p.get("tags","")])).lower()
    if "unisex" in t: return "unisex"
    if "cologne" in t or " men" in t or "for men" in t: return "men"
    if "perfume" in t or "women" in t: return "women"
    return "unisex"
def main():
    cfg=json.load(open(f"{ROOT}/data/config.json"))
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # stock status needs storefront availability; products/<h>.json omits 'available', so use .js endpoint
    def avail(handle):
        req=urllib.request.Request(f"{STORE}/products/{handle}.js",headers={"User-Agent":UA})
        try:
            with urllib.request.urlopen(req,timeout=20) as r: return {v["id"]:v["available"] for v in json.load(r)["variants"]}
        except Exception: return {}
    deals=[]; dropped=[]
    for h in cfg["deals"]:
        p=get(h); time.sleep(0.5)
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
        p=get(h); time.sleep(0.5)
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
    deals.sort(key=lambda d:-d["pct_off"])
    dupes=[]
    for d in cfg["dupes"]:
        d=dict(d); d["price"]=None; d["url"]=None; d["checked"]=None
        if d.get("handle"):
            p=get(d["handle"]); time.sleep(0.5)
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
    json.dump({"updated":now,"deals":deals,"dupes":dupes,"dropped":dropped},open(f"{ROOT}/data/deals.json","w"),indent=1)
    print(f"{len(deals)} live deals, {len(dropped)} dropped {dropped}, {sum(1 for d in dupes if d['price'])}/{len(dupes)} dupes priced")
if __name__=="__main__": main()
