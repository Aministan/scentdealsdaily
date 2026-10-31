#!/usr/bin/env python3
"""Live FragranceNet prices for bottles we track.

Product pages are plain https://www.fragrancenet.com/ URLs. Rakuten deep links
are built later, in build.py, and are never requested here. A miss keeps the
last checked FragranceNet price instead of inventing one. Testers, unboxed
bottles, vials, travel sprays, and refills are ignored.

The price stored for a size is the figure printed on that size ("our price").
The coupon line is a separate promotion and is not the size price.
"""
import datetime, html as html_lib, json, os, re, sys, time, urllib.error, urllib.request
import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETAILER = "FragranceNet"
UA = "Mozilla/5.0 (compatible; ScentDealsDailyBot/1.0; +https://scentdealsdaily.com)"
PAUSE = float(os.environ.get("FN_PAUSE", "0.8"))
JINA = "https://r.jina.ai/"

STATS = {"transient": 0, "total": 0, "blocked": []}

_BLOCK = re.compile(
    r"tester|unboxed|vial|\btravel\b|refill|sample|decant|\bmini\b|gift|\bset\b|"
    r"deodorant|lotion|aftershave|\bsplash\b|\boil\b",
    re.I,
)
_ROW = re.compile(
    r"(?P<qty>\d*\.?\d+)\s*oz(?P<extra>(?:\s+[A-Za-z][A-Za-z'&.-]*){0,6})?\s*\$\s*(?P<price>\d+\.\d{2})",
    re.I,
)
_OUR = re.compile(r"our price:\s*\$\s*(\d+\.\d{2})", re.I)
_RETAIL = re.compile(r"retail price:\s*\$\s*(\d+\.\d{2})", re.I)
_HEAD = re.compile(
    r"(eau\s+de\s+(?:parfum|toilette)|parfum\s+spray|toilette\s+spray).{0,80}?(\d*\.?\d+)\s*oz",
    re.I,
)


def _log(msg):
    print(msg, file=sys.stderr)


def oz_of(text):
    m = re.search(r"(\d*\.?\d+)\s*oz", text or "", re.I)
    return float(m.group(1)) if m else None


def conc_key(text):
    t = (text or "").lower().replace("é", "e")
    if "toilette" in t or re.search(r"\bedt\b", t):
        return "edt"
    if re.search(r"\beau de parfum\b|\bedp\b", t) or ("parfum" in t and "eau" in t):
        return "edp"
    if re.search(r"\bparfum\b", t):
        return "parfum"
    return ""


def plain_text(raw):
    text = raw or ""
    if text.lstrip().startswith("{") and "content" in text[:500]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            content = (inner or {}).get("content") or ""
            if content:
                text = content
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html_lib.unescape(text)
    return text


def challenged(text):
    head = (text or "")[:1800].lower()
    return any(s in head for s in (
        "just a moment", "security check", "cf-challenge", "cdn-cgi/challenge",
        "authenticationrequirederror", "you have been blocked",
    ))


def parse_page(raw, url):
    """Sizes, our-price, and retail from a product page. None when it is not a product."""
    text = plain_text(raw)
    if challenged(text):
        return None
    head = _HEAD.search(text)
    if not head or not _OUR.search(text):
        return None
    heading_oz = float(head.group(2))
    our = float(_OUR.search(text).group(1))
    retail_m = _RETAIL.search(text)
    retail = float(retail_m.group(1)) if retail_m else None
    conc = conc_key(head.group(0) + " " + (url or ""))
    variants = []
    seen = set()
    for m in _ROW.finditer(text):
        extra = (m.group("extra") or "").strip()
        qty = float(m.group("qty"))
        price = float(m.group("price"))
        key = (qty, extra.lower(), price)
        if key in seen:
            continue
        seen.add(key)
        variants.append({"oz": qty, "extra": extra, "price": price, "blocked": bool(_BLOCK.search(extra))})
    # Pages that only state the selected size in the heading still have our price.
    if not any(abs(v["oz"] - heading_oz) < 0.02 and not v["blocked"] for v in variants):
        variants.append({"oz": heading_oz, "extra": "", "price": our, "blocked": False})
    stock = True
    lead = text[:1800]
    if re.search(r"\bonly\s+0\s+left\b", lead, re.I) or re.search(r"\b(out of stock|sold out)\b", lead, re.I):
        stock = False
    return {
        "url": url.split("#")[0],
        "heading_oz": heading_oz,
        "our": our,
        "retail": retail,
        "conc": conc,
        "variants": variants,
        "in_stock": stock,
    }


def pick(page, size):
    """The in-stock sealed variant for this size, or None."""
    if not page or not page.get("in_stock"):
        return None
    want = oz_of(size)
    if want is None:
        return None
    cands = [v for v in page["variants"] if abs(v["oz"] - want) < 0.02 and not v["blocked"]]
    if not cands:
        return None
    plain = [v for v in cands if not v["extra"]]
    pool = plain or cands
    # Prefer the row that matches the heading's own "our price" when this is that size.
    if abs(page["heading_oz"] - want) < 0.02:
        same = [v for v in pool if abs(v["price"] - page["our"]) < 0.001]
        if same:
            pool = same
    chosen = sorted(pool, key=lambda v: (0 if not v["extra"] else 1, v["price"]))[0]
    was = None
    if page.get("retail") and abs(page["heading_oz"] - want) < 0.02 and page["retail"] > chosen["price"]:
        was = round(page["retail"], 2)
    label = _size_label(chosen["oz"])
    return {
        "retailer": RETAILER,
        "price": round(chosen["price"], 2),
        "was": was,
        "size": label,
        "url": page["url"],
        "in_stock": True,
        "conc": page["conc"],
    }


def _size_label(oz):
    text = f"{oz:.2f}".rstrip("0").rstrip(".")
    if "." not in text:
        text = str(int(round(oz))) if abs(oz - round(oz)) < 0.001 else text
    return f"{text} oz"


def _same_bottle(deal_size, offer_size):
    a, b = oz_of(deal_size), oz_of(offer_size)
    return a is not None and b is not None and abs(a - b) < 0.051


def _close_enough(deal_size, offer_size):
    """100 ml is labeled 3.3 oz or 3.4 oz; 50 ml is 1.6 oz or 1.7 oz."""
    a, b = oz_of(deal_size), oz_of(offer_size)
    if a is None or b is None:
        return False
    if abs(a - b) < 0.051:
        return True
    pair = tuple(sorted((round(a, 2), round(b, 2))))
    return pair in {(1.6, 1.7), (3.3, 3.4)}


def _pct(price, was):
    if not was or was <= price:
        return 0
    return int(round((1 - price / was) * 100))


def _apply_match(deal, offer, now):
    if not _close_enough(deal.get("size"), offer["size"]):
        _log(f"  fn size miss {deal.get('id')} site {deal.get('size')} page {offer['size']}")
        return False
    deal_conc = conc_key(f"{deal.get('type') or ''} {deal.get('name') or ''}")
    if deal_conc and offer.get("conc") and deal_conc != offer["conc"]:
        _log(f"  fn conc miss {deal.get('id')} {deal_conc} vs {offer['conc']}")
        return False
    comp = {
        "retailer": RETAILER,
        "price": offer["price"],
        "url": offer["url"],
        "checked": now,
        "size": offer["size"],
    }
    comps = [c for c in (deal.get("comps") or []) if c.get("retailer") != RETAILER]
    if not comps and deal.get("url") and deal.get("price") is not None:
        comps.append({
            "retailer": deal.get("retailer"),
            "price": deal.get("price"),
            "url": deal.get("url"),
            "checked": deal.get("checked") or now,
        })
    comps.append(comp)
    deal["comps"] = comps
    deal["fn"] = {
        "price": offer["price"],
        "was": offer.get("was"),
        "url": offer["url"],
        "size": offer["size"],
    }
    if _same_bottle(deal.get("size"), offer["size"]) and offer["price"] < float(deal.get("price") or 10**9):
        was = offer.get("was")
        was_label = None
        if not was:
            was = deal.get("was")
            was_label = deal.get("was_label")
        pct = _pct(offer["price"], was)
        if was and pct >= 15:
            previous = {
                "retailer": deal.get("retailer"),
                "price": deal.get("price"),
                "url": deal.get("url"),
            }
            deal["price"] = offer["price"]
            deal["retailer"] = RETAILER
            deal["url"] = offer["url"]
            deal["was"] = round(float(was), 2)
            deal["pct_off"] = pct
            deal["checked"] = now
            deal["in_stock"] = True
            if offer.get("was"):
                deal.pop("was_label", None)
            elif was_label:
                deal["was_label"] = was_label
            if previous.get("url") and previous.get("retailer") != RETAILER:
                deal["also"] = previous
            _log(f"  fn primary {deal.get('id')} ${offer['price']:.2f} ({pct}% off)")
            return True
    _log(f"  fn comp {deal.get('id')} ${offer['price']:.2f} {offer['size']}")
    return True


def _standalone_row(spec, offer, now):
    was = offer.get("was")
    if not was or was <= offer["price"]:
        return None
    pct = _pct(offer["price"], was)
    if pct < 15:
        return None
    row = {
        "id": spec["id"],
        "brand": spec["brand"],
        "name": spec["name"],
        "size": offer["size"] if not spec.get("size_label") else spec["size_label"],
        "type": spec.get("type") or "",
        "gender": spec.get("gender") or "unisex",
        "price": offer["price"],
        "was": round(float(was), 2),
        "pct_off": pct,
        "retailer": RETAILER,
        "url": offer["url"],
        "image": spec.get("image") or "",
        "checked": now,
        "in_stock": True,
        "fn": {
            "price": offer["price"],
            "was": offer.get("was"),
            "url": offer["url"],
            "size": offer["size"],
        },
        "comps": [{
            "retailer": RETAILER,
            "price": offer["price"],
            "url": offer["url"],
            "checked": now,
            "size": offer["size"],
        }],
    }
    if spec.get("url_size"):
        row["url_size"] = True
    # Show the size exactly as the page printed it.
    row["size"] = offer["size"]
    return row


def _targets(cfg):
    rows = cfg.get("fragrancenet") if isinstance(cfg, dict) else None
    return rows or []


def fetch_text(url):
    """GET a plain FragranceNet product page. Never a tracking URL."""
    safe = links.safe_request_url(url)
    if not safe or links.is_tracking_url(safe) or links.is_internal_redirect(safe):
        _log("  ! fn refused affiliate tracking url (not requested)")
        return "blocked", ""
    if not links.host_is(links.host_of(safe), "fragrancenet.com"):
        _log(f"  ! fn refused non-product host {safe}")
        return "blocked", ""
    STATS["total"] += 1
    status, body = _direct(safe)
    if status == "ok" and not challenged(body):
        return "ok", body
    if status == "missing":
        return "missing", ""
    parsed, st = _via_reader(safe)
    if st == "ok" and parsed and not challenged(parsed):
        return "ok", parsed
    if st == "missing":
        return "missing", ""
    STATS["transient"] += 1
    STATS["blocked"].append(safe)
    return "blocked", ""


def _direct(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            final = r.geturl()
            if links.is_tracking_url(final) or not links.host_is(links.host_of(final), "fragrancenet.com"):
                return "blocked", ""
            return "ok", r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "missing", ""
        return "blocked", ""
    except Exception as e:
        _log(f"  ! fn direct {e}")
        return "blocked", ""


def _via_reader(url):
    req = urllib.request.Request(JINA + url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=70) as r:
            return r.read().decode("utf-8", "replace"), "ok"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "", "missing"
        _log(f"  ! fn reader {e.code}")
        return "", "blocked"
    except Exception as e:
        _log(f"  ! fn reader {e}")
        return "", "blocked"


def attach(deals, now=None, pages=None):
    """Add FragranceNet offers from config. `pages` skips the network (tests)."""
    cfg = json.load(open(f"{ROOT}/data/config.json"))
    targets = _targets(cfg)
    if not targets:
        return {"blocked": [], "matched": 0}
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    by_id = {d.get("id"): d for d in deals}
    urls = []
    for t in targets:
        if t.get("url") and t["url"] not in urls:
            urls.append(t["url"])
    cache = {}
    blocked = []
    if pages is None:
        for url in urls:
            status, body = fetch_text(url)
            time.sleep(PAUSE)
            if status == "ok":
                cache[url] = parse_page(body, url)
            elif status == "blocked":
                blocked.append(url)
            else:
                _log(f"  fn missing {url}")
    else:
        for url, raw in pages.items():
            cache[url] = parse_page(raw, url)
    matched = 0
    for t in targets:
        url = t.get("url")
        if url in blocked:
            continue
        page = cache.get(url)
        offer = pick(page, t.get("size"))
        if not offer:
            _log(f"  fn skip {url} {t.get('size')}")
            continue
        if t.get("match_id"):
            deal = by_id.get(t["match_id"])
            if deal and _apply_match(deal, offer, now):
                matched += 1
        spec = t.get("standalone")
        if spec:
            row = _standalone_row(spec, offer, now)
            if not row:
                _log(f"  fn standalone under 15% or no retail {spec.get('id')}")
                continue
            old = by_id.get(row["id"])
            if old is not None:
                idx = deals.index(old)
                deals[idx] = row
                by_id[row["id"]] = row
            else:
                deals.append(row)
                by_id[row["id"]] = row
            matched += 1
            _log(f"  fn deal {row['id']} ${row['price']:.2f} was ${row['was']:.2f} ({row['pct_off']}%)")
    _log(f"fragrancenet: {matched} offers, {len(blocked)} blocked fetches")
    return {"blocked": blocked, "matched": matched}


def restore(deals, previous, blocked_urls):
    """Put back FragranceNet prices when those product pages could not be fetched."""
    if not previous or not blocked_urls:
        return 0
    blocked = set(blocked_urls)
    by_id = {d.get("id"): d for d in deals}
    kept = 0
    for old in previous:
        fn = old.get("fn") or {}
        url = fn.get("url") or (old.get("url") if old.get("retailer") == RETAILER else None)
        if not url or url not in blocked:
            continue
        current = by_id.get(old.get("id"))
        if current is None:
            if old.get("retailer") == RETAILER or fn:
                deals.append(old)
                by_id[old.get("id")] = old
                kept += 1
            continue
        if current.get("fn"):
            continue
        offer = {
            "price": fn.get("price"),
            "was": fn.get("was"),
            "url": fn.get("url") or url,
            "size": fn.get("size") or old.get("size"),
            "conc": conc_key(old.get("type") or ""),
            "retailer": RETAILER,
        }
        if offer["price"] is None:
            continue
        if old.get("retailer") == RETAILER and current.get("retailer") != RETAILER and current.get("id") == old.get("id"):
            # Standalone rows are appended above when missing. A matched deal keeps its comp.
            pass
        if _apply_match(current, offer, old.get("checked") or current.get("checked")):
            kept += 1
    if kept:
        _log(f"fragrancenet fetch blocked; kept {kept} previously checked offers")
    return kept


# Excerpts copied from the live product pages opened for this retailer.
# Prices below are parsed from these strings; they are not typed in separately.
FIXTURES = {
 "https://www.fragrancenet.com/cologne/calvin-klein/ck-free/edt": """
## Eau De Toilette Spray 3.4 oz
retail price: $89.00
our price: $30.99
Price with Coupon:$20.76 Save $68.24 (77%)
Hurry, only 10 left!
1.7 oz$24.99
3.4 oz$30.99
3.4 oz Tester$26.99
""",
 "https://www.fragrancenet.com/fragrances/calvin-klein/ck-everyone/edt": """
## Eau De Toilette Spray 6.7 oz
retail price: $89.00
our price: $56.99
Price with Coupon:$38.18 Save $50.82 (57%)
vial$4.99
0.33 oz$15.99
1.7 oz$28.99
3.3 oz$41.99
3.4 oz Tester$38.99
6.7 oz$56.99
""",
 "https://www.fragrancenet.com/fragrances/calvin-klein/ck-one/edt": """
## Eau De Toilette Spray 6.7 oz
retail price: $89.00
our price: $50.99
Price with Coupon:$34.16 Save $54.84 (62%)
vial$3.99
0.27 oz Travel spray$13.99
0.5 oz$13.99
0.68 oz$17.99
1.6 oz$29.99
3.4 oz$37.99
6.7 oz$50.99
10 oz$79.99
""",
 "https://www.fragrancenet.com/perfume/calvin-klein/eternity/eau-de-parfum": """
## Eau De Parfum Spray 3.3 oz
retail price: $114.00
our price: $52.99
Price with Coupon:$35.50 Save $78.50 (69%)
vial$5.99
0.27 oz Travel spray$15.99
0.33 oz$18.99
1 oz$37.99
1.6 oz$49.99
3.3 oz$52.99
3.3 oz Tester$53.99
""",
 "https://www.fragrancenet.com/perfume/calvin-klein/calvin-klein-beauty/eau-de-parfum": """
## Eau De Parfum Spray 3.3 oz
retail price: $100.00
our price: $45.99
Price with Coupon:$30.81 Save $69.19 (69%)
""",
 "https://www.fragrancenet.com/cologne/gianni-versace/versace-eros/edt": """
## Eau De Toilette Spray 3.4 oz
retail price: $120.00
our price: $112.99
Price with Coupon:$75.70 Save $44.30 (37%)
0.17 oz$12.99
1 oz$62.99
1.7 oz$83.99
3.4 oz$112.99
6.7 oz$149.99
""",
 "https://www.fragrancenet.com/cologne/giorgio-armani/acqua-di-gio/edt": """
## Eau De Toilette Spray 3.4 oz
retail price: $130.00
our price: $129.99
Price with Coupon:$87.09 Save $42.91 (33%)
0.27 oz Travel spray$21.99
0.5 oz$44.99
1 oz Refillable$78.99
1 oz$78.99
1.7 oz$99.99
3.4 oz$129.99
3.4 oz Tester$107.99
6.7 oz$199.99
""",
 "https://www.fragrancenet.com/perfume/valentino/valentino-donna-born-in-roma/eau-de-parfum": """
## Eau De Parfum Spray 3.4 oz
our price: $224.99 Price with Coupon:$150.74
0.2 oz$55.99
0.27 oz Travel spray$29.99
1 oz$130.99
1.7 oz$154.99
3.4 oz$224.99
3.4 oz Tester$199.99
""",
 "https://www.fragrancenet.com/perfume/gianni-versace/versace-bright-crystal-absolu/eau-de-parfum": """
## Eau De Parfum Spray (New Packaging) 3 oz
our price: $126.99 Price with Coupon:$85.08
0.27 oz Travel spray$22.99
1 oz New Packaging$63.99
1 oz$58.99
1.7 oz New Packaging$90.99
3 oz New Packaging$126.99
""",
 "https://www.fragrancenet.com/perfume/clinique/happy/eau-de-parfum": """
## Eau De Parfum Spray 3.4 oz
retail price: $108.00
our price: $57.99
Price with Coupon:$38.85 Save $69.15 (64%)
0.27 oz Travel spray$19.99
1 oz$31.99
1.7 oz$40.99
3.4 oz$57.99
""",
 "https://www.fragrancenet.com/cologne/burberry/burberry-touch/edt": """
## Eau De Toilette Spray (New Packaging) 3.3 oz
retail price: $105.00
our price: $57.99
Price with Coupon:$38.85 Save $66.15 (63%)
0.27 oz Travel spray$17.99
1.6 oz New Packaging$41.99
3.3 oz New Packaging$57.99
3.3 oz Tester New Packaging$47.99
""",
 "https://www.fragrancenet.com/perfume/dolce-and-gabbana/d-and-g-light-blue/edt": """
## Eau De Toilette Spray 3.3 oz
retail price: $150.00
our price: $91.99
Price with Coupon:$61.63 Save $88.37 (59%)
vial 0.05 oz$4.99
0.27 oz Travel spray$19.99
1.6 oz$64.99
1.7 oz New Packaging$62.99
3.3 oz$91.99
3.3 oz Tester$73.99
6.7 oz$139.99
""",
 "https://www.fragrancenet.com/cologne/davidoff/cool-water/edt": """
## Eau De Toilette Spray 4.2 oz
retail price: $103.00
our price: $39.99
Price with Coupon:$26.79 Save $76.21 (74%)
2.5 oz$31.99
4.2 oz$39.99
4.2 oz Unboxed$35.99
6.7 oz$59.99
""",
 "https://www.fragrancenet.com/perfume/calvin-klein/obsession/eau-de-parfum": """
## Eau De Parfum Spray 3.3 oz
retail price: $100.00
our price: $40.99
Price with Coupon:$27.46 Save $72.54 (73%)
0.27 oz Travel spray$14.99
1.6 oz$29.99
3.3 oz$40.99
3.4 oz Tester$35.99
""",
 "https://www.fragrancenet.com/cologne/calvin-klein/eternity/edt": """
## Eau De Toilette Spray (New Packaging) 3.3 oz
retail price: $105.00
our price: $51.99
Price with Coupon:$34.83 Save $70.17 (67%)
vial$3.99
1 oz New Packaging$30.99
1.6 oz New Packaging$42.99
3.3 oz New Packaging$51.99
6.7 oz New Packaging$70.99
""",
 "https://www.fragrancenet.com/perfume/calvin-klein/euphoria/eau-de-parfum": """
## Eau De Parfum Spray 3.3 oz
retail price: $114.00
our price: $83.99
Price with Coupon:$56.27 Save $57.73 (51%)
0.27 oz Travel spray$18.99
0.5 oz$27.99
1.6 oz$59.99
3.3 oz$83.99
5.4 oz$104.99
""",
}


def self_check():
    expect = {
        ("https://www.fragrancenet.com/cologne/calvin-klein/ck-free/edt", "3.4 oz"): (30.99, 89.0),
        ("https://www.fragrancenet.com/fragrances/calvin-klein/ck-everyone/edt", "3.3 oz"): (41.99, None),
        ("https://www.fragrancenet.com/fragrances/calvin-klein/ck-everyone/edt", "6.7 oz"): (56.99, 89.0),
        ("https://www.fragrancenet.com/fragrances/calvin-klein/ck-one/edt", "1.6 oz"): (29.99, None),
        ("https://www.fragrancenet.com/fragrances/calvin-klein/ck-one/edt", "6.7 oz"): (50.99, 89.0),
        ("https://www.fragrancenet.com/perfume/calvin-klein/eternity/eau-de-parfum", "3.3 oz"): (52.99, 114.0),
        ("https://www.fragrancenet.com/perfume/calvin-klein/calvin-klein-beauty/eau-de-parfum", "3.3 oz"): (45.99, 100.0),
        ("https://www.fragrancenet.com/cologne/gianni-versace/versace-eros/edt", "1.7 oz"): (83.99, None),
        ("https://www.fragrancenet.com/cologne/giorgio-armani/acqua-di-gio/edt", "3.4 oz"): (129.99, 130.0),
        ("https://www.fragrancenet.com/perfume/valentino/valentino-donna-born-in-roma/eau-de-parfum", "1.7 oz"): (154.99, None),
        ("https://www.fragrancenet.com/perfume/gianni-versace/versace-bright-crystal-absolu/eau-de-parfum", "3 oz"): (126.99, None),
        ("https://www.fragrancenet.com/perfume/clinique/happy/eau-de-parfum", "1 oz"): (31.99, None),
        ("https://www.fragrancenet.com/perfume/clinique/happy/eau-de-parfum", "3.4 oz"): (57.99, 108.0),
        ("https://www.fragrancenet.com/cologne/burberry/burberry-touch/edt", "3.3 oz"): (57.99, 105.0),
        ("https://www.fragrancenet.com/perfume/dolce-and-gabbana/d-and-g-light-blue/edt", "3.3 oz"): (91.99, 150.0),
        ("https://www.fragrancenet.com/cologne/davidoff/cool-water/edt", "4.2 oz"): (39.99, 103.0),
        ("https://www.fragrancenet.com/perfume/calvin-klein/obsession/eau-de-parfum", "3.3 oz"): (40.99, 100.0),
        ("https://www.fragrancenet.com/cologne/calvin-klein/eternity/edt", "3.3 oz"): (51.99, 105.0),
        ("https://www.fragrancenet.com/perfume/calvin-klein/euphoria/eau-de-parfum", "3.3 oz"): (83.99, 114.0),
    }
    bad = 0
    for (url, size), (price, was) in expect.items():
        offer = pick(parse_page(FIXTURES[url], url), size)
        if not offer or offer["price"] != price or offer.get("was") != was:
            bad += 1
            _log(f"FAIL {size} {url} -> {offer} expected {price} was {was}")
        if offer and _BLOCK.search(offer["size"]):
            bad += 1
    # Testers and the coupon price must not win.
    eros = parse_page(FIXTURES["https://www.fragrancenet.com/cologne/gianni-versace/versace-eros/edt"], "https://www.fragrancenet.com/cologne/gianni-versace/versace-eros/edt")
    if any(v["price"] == 75.70 for v in eros["variants"]):
        bad += 1
        _log("FAIL coupon price parsed as a size")
    if bad:
        raise SystemExit(f"fragrancenet parser check failed ({bad})")
    print(f"fragrancenet parser ok ({len(expect)} sizes)")


TARGETS = [
 {"url":"https://www.fragrancenet.com/cologne/calvin-klein/ck-free/edt","size":"3.4 oz","match_id":"calvin-klein-free-mens-eau-de-toilette-spray"},
 {"url":"https://www.fragrancenet.com/fragrances/calvin-klein/ck-everyone/edt","size":"3.3 oz","match_id":"ck-everyone-unisex-fragrance"},
 {"url":"https://www.fragrancenet.com/fragrances/calvin-klein/ck-one/edt","size":"1.6 oz","match_id":"calvin-klein-ck-one-eau-de-toilette-unisex-fragrance"},
 {"url":"https://www.fragrancenet.com/perfume/calvin-klein/eternity/eau-de-parfum","size":"3.3 oz","match_id":"calvin-klein-eternity-womens-eau-de-parfum-spray"},
 {"url":"https://www.fragrancenet.com/perfume/calvin-klein/calvin-klein-beauty/eau-de-parfum","size":"3.3 oz","match_id":"calvin-klein-beauty-perfume-eau-de-parfum-for-women"},
 {"url":"https://www.fragrancenet.com/cologne/gianni-versace/versace-eros/edt","size":"1.7 oz","match_id":"versace-eros-cologne-eau-de-toilette-for-men"},
 {"url":"https://www.fragrancenet.com/cologne/giorgio-armani/acqua-di-gio/edt","size":"3.4 oz","match_id":"giorgio-armani-acqua-di-gio-eau-de-toilette-cologne-for-men"},
 {"url":"https://www.fragrancenet.com/perfume/valentino/valentino-donna-born-in-roma/eau-de-parfum","size":"1.7 oz","match_id":"valentino-donna-born-in-roma-perfume-eau-de-parfum-for-women"},
 {"url":"https://www.fragrancenet.com/perfume/gianni-versace/versace-bright-crystal-absolu/eau-de-parfum","size":"3 oz","match_id":"bright-crystal-absolu-by-versace-for-women-eau-de-parfum-spray"},
 {"url":"https://www.fragrancenet.com/perfume/clinique/happy/eau-de-parfum","size":"1 oz","match_id":"clinique-happy-women-eau-de-parfum-spray"},
 {"url":"https://www.fragrancenet.com/fragrances/calvin-klein/ck-one/edt","size":"6.7 oz","standalone":{
    "id":"calvin-klein-ck-one-eau-de-toilette-6-7-oz","brand":"Calvin Klein","name":"CK One","gender":"unisex","type":"Eau de Toilette",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/115760.png","url_size":True}},
 {"url":"https://www.fragrancenet.com/fragrances/calvin-klein/ck-everyone/edt","size":"6.7 oz","standalone":{
    "id":"calvin-klein-ck-everyone-eau-de-toilette-6-7-oz","brand":"Calvin Klein","name":"CK Everyone","gender":"unisex","type":"Eau de Toilette"}},
 {"url":"https://www.fragrancenet.com/cologne/burberry/burberry-touch/edt","size":"3.3 oz","standalone":{
    "id":"burberry-touch-cologne-eau-de-toilette","brand":"Burberry","name":"Touch Cologne","gender":"men","type":"Eau de Toilette",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/340160.png"}},
 {"url":"https://www.fragrancenet.com/perfume/dolce-and-gabbana/d-and-g-light-blue/edt","size":"3.3 oz","standalone":{
    "id":"dolce-gabbana-light-blue-eau-de-toilette","brand":"Dolce & Gabbana","name":"Light Blue Perfume","gender":"women","type":"Eau de Toilette",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/120682.png"}},
 {"url":"https://www.fragrancenet.com/cologne/davidoff/cool-water/edt","size":"4.2 oz","standalone":{
    "id":"davidoff-cool-water-eau-de-toilette","brand":"Davidoff","name":"Cool Water Cologne","gender":"men","type":"Eau de Toilette",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/115948.png"}},
 {"url":"https://www.fragrancenet.com/perfume/clinique/happy/eau-de-parfum","size":"3.4 oz","standalone":{
    "id":"clinique-happy-eau-de-parfum-3-4-oz","brand":"Clinique","name":"Happy Perfume","gender":"women","type":"Eau de Parfum",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/120800.png","url_size":True}},
 {"url":"https://www.fragrancenet.com/perfume/calvin-klein/obsession/eau-de-parfum","size":"3.3 oz","standalone":{
    "id":"calvin-klein-obsession-eau-de-parfum","brand":"Calvin Klein","name":"Obsession Perfume","gender":"women","type":"Eau de Parfum",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/120689.png"}},
 {"url":"https://www.fragrancenet.com/cologne/calvin-klein/eternity/edt","size":"3.3 oz","standalone":{
    "id":"calvin-klein-eternity-cologne-eau-de-toilette","brand":"Calvin Klein","name":"Eternity Cologne","gender":"men","type":"Eau de Toilette",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/412684.png"}},
 {"url":"https://www.fragrancenet.com/perfume/calvin-klein/euphoria/eau-de-parfum","size":"3.3 oz","standalone":{
    "id":"calvin-klein-euphoria-eau-de-parfum","brand":"Calvin Klein","name":"Euphoria Perfume","gender":"women","type":"Eau de Parfum",
    "image":"https://cdn.fragrancenet.com/images/photos/250x250/139842.png"}},
]


if __name__ == "__main__":
    self_check()
