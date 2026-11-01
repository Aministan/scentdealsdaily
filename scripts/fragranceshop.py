#!/usr/bin/env python3
"""Live FragranceShop prices for products we already track.

FragranceShop is WooCommerce. Per-size prices come from the public Store API
(a variation is one sealed size). Direct requests often meet a Cloudflare
challenge (403); we retry with backoff, then read the same JSON through a
browser reader. Testers, unboxed bottles, oils and body products are ignored.
Nothing here estimates a price: a miss stays Perfumania-only.
"""
import json, os, re, time, urllib.parse, urllib.request, urllib.error, sys
import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = "https://www.fragranceshop.com"
API = STORE + "/wp-json/wc/store/v1/products"
UA = "Mozilla/5.0 (compatible; ScentDealsDailyBot/1.0; +https://scentdealsdaily.com)"
PAUSE = float(os.environ.get("FS_PAUSE", "3.2"))  # jina free tier is ~20/min; direct calls are faster
JINA = "https://r.jina.ai/"
RETAILER = "FragranceShop"

# Variation labels we will not price. Sealed retail fragrance sprays only.
_BLOCK = re.compile(
    r"tester|\bunboxed\b|un-boxed|without box|no box|\boil\b|roll-?on|deodorant|"
    r"lotion|\bbalm\b|shower|body cream|body wash|\bsoap\b|gift set|coffret|\bset\b|"
    r"\bsample\b|\bvial\b|decant|aftershave|after shave|after-shave|body spray|"
    r"hair mist|body mist|miniature|\bmini\b|\bsplash\b",
    re.I,
)
_GENERIC = {
    "eau", "de", "toilette", "parfum", "perfume", "cologne", "spray", "for", "men", "man",
    "mens", "men's", "women", "woman", "womens", "women's", "by", "the", "a", "an", "of",
    "oz", "fragrance", "unisex", "edt", "edp", "edc", "pour", "homme", "femme", "new",
    "ml", "and", "in", "le", "la", "el", "du", "des", "scent",
}
# Extra words that mean a different fragrance when only one side has them.
_FLANKER = {
    "absolu", "absolute", "absolue", "air", "blossom", "coral", "elixir", "extreme",
    "flame", "fresh", "gold", "intense", "intensely", "legend", "light", "night",
    "noir", "oud", "parfum", "profondo", "profumo", "sport", "summer", "tonic",
    "unlimited", "winter", "elixir", "fantasy", "neroli", "wood",
}


def _log(msg):
    print(msg, file=sys.stderr)


STATS = {"transient": 0, "total": 0}


class Client:
    """GET JSON with the same backoff shape as the Perfumania fetcher."""

    def __init__(self):
        self.transient = 0
        self.total = 0
        self._next = 0.0
        self._cache = {}

    def _wait(self):
        d = self._next - time.time()
        if d > 0:
            time.sleep(d)

    def _pace(self, seconds):
        self._next = time.time() + seconds

    def get_json(self, url, tries=6):
        safe = links.safe_request_url(url)
        if not safe:
            _log("  ! fs refused affiliate tracking url (not requested)")
            return None
        url = safe
        if url in self._cache:
            return self._cache[url]
        self.total += 1
        STATS["total"] += 1
        self._wait()
        last = None
        for i in range(tries):
            body, code, wait = self._direct(url)
            if body is not None:
                self._pace(0.4)
                self._cache[url] = body
                return body
            if code == 404:
                _log(f"  ! fs 404 {url}")
                self._pace(0.4)
                self._cache[url] = None
                return None
            if code in (403, 429, 500, 502, 503, 504, None) and i < tries - 1 and code != 403:
                w = wait if wait is not None else min(60, 4 * 2 ** i)
                _log(f"  ~ fs {code} retry in {w:.0f}s")
                time.sleep(w)
                last = code
                continue
            # Cloudflare challenge, or retries exhausted: one reader attempt on 403/challenge.
            if code == 403 or (isinstance(body, str)):
                parsed, status, ra = self._via_reader(url)
                if parsed is not None:
                    self._pace(PAUSE)
                    self._cache[url] = parsed
                    return parsed
                if status == 429 and i < tries - 1:
                    w = ra if ra is not None else min(60, 4 * 2 ** i)
                    _log(f"  ~ fs reader 429 retry in {w:.0f}s")
                    time.sleep(w)
                    continue
            last = code
            break
        _log(f"  ! fs failed {url} ({last})")
        self.transient += 1
        STATS["transient"] += 1
        self._pace(0.4)
        return None

    def _direct(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read()
                if _challenged(raw):
                    return None, 403, None
                return json.loads(raw.decode("utf-8")), r.status, None
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After") if e.headers else None
            wait = float(ra) if ra and ra.replace(".", "", 1).isdigit() else None
            return None, e.code, wait
        except Exception as e:
            _log(f"  ! fs direct {e}")
            return None, None, None

    def _via_reader(self, url):
        req = urllib.request.Request(
            JINA + url,
            headers={"User-Agent": UA, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=70) as r:
                raw = r.read().decode("utf-8", "replace")
                ra = r.headers.get("Retry-After")
                wait = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else None
                rem = r.headers.get("x-ratelimit-remaining") or ""
                if rem.startswith("0"):
                    self._pace(max(PAUSE, 15))
                return _reader_json(raw), r.status, wait
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After") if e.headers else None
            wait = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else None
            _log(f"  ! fs reader {e.code} {url.split('?',1)[0][-48:]}")
            return None, e.code, wait
        except Exception as e:
            _log(f"  ! fs reader {e}")
            return None, None, None


def _challenged(raw):
    head = raw[:800].lower()
    return b"just a moment" in head or b"cf-challenge" in head or b"cdn-cgi/challenge" in head


def _reader_json(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list) or (isinstance(data, dict) and "id" in data and "prices" in data):
        return data
    content = ""
    if isinstance(data, dict):
        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        content = (inner or {}).get("content") or ""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # reader sometimes prepends a title line
    start = min((i for i in (text.find("["), text.find("{")) if i >= 0), default=-1)
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def money(prices):
    """Store API amounts are minor units (cents) as strings."""
    if not prices:
        return None, None
    unit = int(prices.get("currency_minor_unit") or 2)
    scale = 10 ** unit
    code = (prices.get("currency_code") or "USD").upper()
    if code != "USD":
        return None, None

    def conv(key):
        v = prices.get(key)
        if v in (None, "", "0", 0):
            return None
        try:
            return round(int(v) / scale, 2)
        except (TypeError, ValueError):
            return None

    price = conv("price")
    regular = conv("regular_price")
    if price is None:
        return None, None
    if regular is None or regular < price:
        regular = price
    return price, regular


def size_oz(text):
    t = (text or "").lower().replace("–", "-").replace("—", "-")
    m = re.search(r"(\d+)\.(\d+)\s*oz", t)
    if m:
        return round(float(f"{m.group(1)}.{m.group(2)}"), 2)
    m = re.search(r"(\d+)-(\d+)-oz", t)
    if m:
        return round(float(f"{m.group(1)}.{m.group(2)}"), 2)
    m = re.search(r"(\d+)\s*oz", t)
    if m:
        return float(m.group(1))
    return None


def concentration(text):
    t = (text or "").lower().replace("-", " ").replace(".", " ")
    t = re.sub(r"\s+", " ", t)
    # "Eau de Parfum Intense" is its own concentration, not a plain EDP.
    if "eau de parfum intense" in t or re.search(r"\bedp intense\b", t):
        return "edp-intense"
    if "parfum intense" in t:
        return "parfum-intense"
    if "eau de parfum" in t or re.search(r"\bedp\b", t):
        return "edp"
    if "eau de toilette" in t or re.search(r"\bedt\b", t):
        return "edt"
    if "eau de cologne" in t or re.search(r"\bedc\b", t):
        return "edc"
    if "extrait" in t:
        return "extrait"
    if re.search(r"\bparfum\b", t):
        return "parfum"
    return None


def _conc_ok(deal_conc, label, sig):
    got = concentration(label)
    if got == deal_conc:
        return True
    # Perfumania often files an "Intense" flanker under plain Eau de Parfum.
    if "intense" in (sig or []) and {got, deal_conc} == {"edp", "edp-intense"}:
        return True
    return False


def _fold(text):
    import unicodedata
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower().replace("&", " and ").replace("no.", " no ")


def _tokens(text):
    t = re.sub(r"[^a-z0-9]+", " ", _fold(text))
    return [w for w in t.split() if w and w not in _GENERIC and w != "no" and not w.isdigit()]


def _brand_tokens(brand):
    b = (brand or "").lower()
    extra = []
    if "calvin klein" in b or b == "ck":
        extra = ["calvin", "klein", "ck"]
    if "jean paul gaultier" in b or b == "jpg":
        extra += ["jean", "paul", "gaultier", "jpg"]
    if "giorgio armani" in b:
        extra += ["giorgio", "armani", "emporio"]
    if "hugo boss" in b or b == "boss":
        extra += ["hugo", "boss"]
    if "paco rabanne" in b or "rabanne" in b:
        extra += ["paco", "rabanne"]
    if "elizabeth arden" in b:
        extra += ["elizabeth", "arden"]
    if "juicy couture" in b:
        extra += ["juicy", "couture"]
    if "tom ford" in b:
        extra += ["tom", "ford"]
    if "billie eilish" in b:
        extra += ["billie", "eilish"]
    if "bvlgari" in b or "bulgari" in b:
        extra += ["bvlgari", "bulgari"]
    if "lanc" in b:
        extra += ["lancome", "lancôme"]
    return set(_tokens(brand)) | set(extra)


_CONC_WORDS = {"parfum", "extrait"}
_GENDER_WORDS = {"men", "man", "mens", "women", "woman", "womens", "femme", "homme", "male", "female", "pour"}


def signature(text, brand, drop_gender=False):
    ban = _brand_tokens(brand) | _CONC_WORDS
    if drop_gender:
        ban |= _GENDER_WORDS
    out = [w for w in _tokens(text) if w not in ban]
    for n in _numbers(text):
        tok = "no" + n
        if tok not in out:
            out.append(tok)
    return out


def _numbers(text):
    return re.findall(r"\bno\s*\.?\s*(\d+)\b", _fold(text))


def identity(deal):
    """Name tokens, plus flankers that live only in the product handle ('wanted by night')."""
    brand = deal.get("brand") or ""
    name = deal.get("name") or deal.get("dupe") or ""
    handle = (deal.get("id") or deal.get("handle") or "").replace("-", " ")
    sig = signature(name, brand, drop_gender=False)
    # 'for women' in a handle is gender, not the fragrance name. Keep real name words
    # like Woman / Pour Homme when they are in the title itself.
    for w in signature(handle, brand, drop_gender=True):
        if w not in sig:
            sig.append(w)
    return sig


def queries_for(deal):
    """A few searches. The brand is often absent from the FragranceShop title."""
    brand = deal.get("brand") or ""
    name = deal.get("name") or deal.get("dupe") or ""
    sig = identity(deal)
    nums = _numbers(f"{name} {(deal.get('id') or deal.get('handle') or '')}")
    qs = []

    def add(q):
        q = re.sub(r"\s+", " ", q or "").strip()
        if q and q.lower() not in [x.lower() for x in qs]:
            qs.append(q)

    add(f"{brand} {name}")
    add(name)
    add(" ".join(sig + [f"no {n}" for n in nums]))
    bl = brand.lower()
    if "calvin klein" in bl:
        add("ck " + " ".join(sig))
    if bl in ("hugo boss", "boss"):
        add("boss " + " ".join(sig))
    if "bvlgari" in bl or "bulgari" in bl:
        add("bulgari " + " ".join(sig))
    if "lanc" in bl:
        add("lancome " + name)
    if "jean paul" in bl:
        add(" ".join(sig))
    return qs[:4]


def _blocked(label):
    return bool(_BLOCK.search(label or ""))


def _gender_ok(deal_gender, product_name):
    if deal_gender in (None, "", "any"):
        return True
    n = _fold(product_name)
    women = bool(re.search(r"\b(women|woman|femme)\b", n))
    men = bool(re.search(r"\b(men|man|homme)\b", n))
    uni = "unisex" in n
    if deal_gender == "women" and men and not women and not uni:
        return False
    if deal_gender == "men" and women and not men and not uni:
        return False
    if deal_gender == "unisex" and (men or women) and not uni:
        # CK One and CK Everyone are unisex; a gendered title is a different bottle
        return False
    return True


def _has_number(name, n):
    folded = _fold(name)
    return n in re.findall(r"\bno\s*\.?\s*(\d+)\b", folded) or f"n {n}" in folded


def _matching_variation(product, conc, oz, sig):
    pname = product.get("name") or ""
    variations = product.get("variations") or []
    if variations:
        for v in variations:
            attrs = v.get("attributes") or []
            label = " ".join(a.get("value") or "" for a in attrs)
            if _blocked(label):
                continue
            if not _conc_ok(conc, label, sig) or size_oz(label) != oz:
                continue
            if not v.get("id"):
                continue
            return label, v["id"]
        return None, None
    if _blocked(pname):
        return None, None
    if _conc_ok(conc, pname, sig) and size_oz(pname) == oz and product.get("id"):
        return pname, product["id"]
    return None, None


def pick_product(deal, products):
    """Return (product, variation label, variation id, reason)."""
    brand = deal.get("brand") or ""
    handle = (deal.get("id") or deal.get("handle") or "").replace("-", " ")
    name = deal.get("name") or deal.get("dupe") or ""
    conc = concentration(f"{deal.get('type') or ''} {name} {handle}")
    oz = size_oz(deal.get("size") or "")
    if oz is None or conc is None:
        return None, None, None, "no size or concentration"
    sig = identity(deal)
    nums = _numbers(f"{name} {handle}")
    cands = []
    for p in products or []:
        if p.get("type") not in (None, "variable", "simple", "variation"):
            continue
        pname = p.get("name") or ""
        if _blocked(pname):
            continue
        if not _gender_ok(deal.get("gender"), pname):
            continue
        psig = signature(pname, brand, drop_gender=False)
        # "Azzaro Cologne" / "Coach for Men" have no name token left after the brand.
        # Only the house namesake (no extra words, no "No. 2") is safe to pair with those.
        if not sig and (signature(pname, brand, drop_gender=True) or _numbers(pname)):
            continue
        if any(w not in psig for w in sig):
            continue
        # a leftover word is a different fragrance (Flora, Profondo, Shock, No.2)
        extra = [w for w in psig if w not in sig and w not in _GENDER_WORDS]
        if extra:
            continue
        if nums and not all(_has_number(pname, n) for n in nums):
            continue
        label, vid = _matching_variation(p, conc, oz, sig)
        if not label:
            continue
        score = abs(len(psig) - len(sig))
        cands.append((score, len(psig), p, label, vid))
    if not cands:
        return None, None, None, "no exact sealed match"
    cands.sort(key=lambda c: (c[0], c[1], c[2].get("name") or ""))
    def sig_key(p):
        return tuple(sorted(signature(p.get("name") or "", brand, drop_gender=True)))
    # Woman vs Femme can share a score with different names. Two listings of one name cannot.
    if len(cands) > 1 and sig_key(cands[0][2]) != sig_key(cands[1][2]) and (cands[0][0], cands[0][1]) == (cands[1][0], cands[1][1]):
        return None, None, None, "ambiguous: " + " | ".join(c[2]["name"] for c in cands[:3])
    best = cands[0]
    return best[2], best[3], best[4], None


def search(client, query):
    q = urllib.parse.urlencode({"search": query, "per_page": 20})
    data = client.get_json(f"{API}?{q}")
    if isinstance(data, dict) and data.get("id"):
        return [data]
    return data if isinstance(data, list) else []


def variation(client, vid):
    data = client.get_json(f"{API}/{int(vid)}")
    if not isinstance(data, dict) or not data.get("prices"):
        return None
    if data.get("is_in_stock") is False or data.get("is_purchasable") is False:
        return None
    label = data.get("variation") or data.get("name") or ""
    if _blocked(label) or _blocked(data.get("slug") or ""):
        return None
    price, regular = money(data.get("prices"))
    if price is None:
        return None
    url = (data.get("permalink") or "").split("&add-to-cart")[0]
    # permalink already selects the size; drop an add-to-cart that the API sometimes appends
    url = url.replace("&variation_id=" + str(data.get("id")), "")
    if "add-to-cart" in url:
        url = data.get("permalink") or url
        url = re.sub(r"[&?](variation_id|add-to-cart)=[^&]*", "", url).rstrip("?&")
    if not url.startswith(STORE):
        return None
    return {
        "retailer": RETAILER,
        "price": price,
        "was": regular,
        "url": url,
        "in_stock": True,
        "variation": data.get("variation") or "",
        "name": data.get("name") or "",
        "id": data.get("id"),
    }


def lookup(client, deal):
    """Find the same brand, name, concentration and size. None if it isn't reliable."""
    qs = queries_for(deal)
    product = label = vid = why = None
    used = None
    seen = []
    for q in qs:
        products = search(client, q)
        # pages we already considered stay in the pool so a later query can add the right one
        for p in products:
            if all(p.get("id") != s.get("id") for s in seen):
                seen.append(p)
        product, label, vid, why = pick_product(deal, seen)
        used = q
        if product and vid:
            break
        if why and str(why).startswith("ambiguous"):
            break
    if not product or not vid:
        if why:
            _log(f"  fs skip {deal.get('brand')} {deal.get('name')}: {why}")
        return None
    offer = variation(client, vid)
    if not offer:
        return None
    deal_conc = concentration(f"{deal.get('type') or ''} {deal.get('name') or ''} {deal.get('id') or deal.get('handle') or ''}")
    if not _conc_ok(deal_conc, offer.get("variation") or label, identity(deal)):
        return None
    if size_oz(offer.get("variation") or label) != size_oz(deal.get("size") or ""):
        return None
    offer["matched"] = product.get("name")
    offer["query"] = used
    return offer


def dupe_as_deal(d):
    name = d.get("dupe") or ""
    brand = name.split()[0]
    for prefix in ("Ariana Grande", "Al Haramain", "Jean Paul Gaultier", "Club de Nuit"):
        if name.lower().startswith(prefix.lower()):
            brand = prefix
            break
    return {
        "brand": brand,
        "name": name,
        "dupe": name,
        "handle": d.get("handle") or "",
        "id": d.get("handle") or "",
        "size": d.get("size"),
        "type": d.get("type") or "",
        "gender": None,
    }


def attach(deals, dupes=None):
    """Add a FragranceShop offer where the exact bottle can be priced. Mutates deals."""
    client = Client()
    matched = 0
    for d in deals:
        offer = lookup(client, d)
        if not offer:
            _log(f"  fs miss {d.get('brand')} {d.get('name')} {d.get('size')}")
            continue
        matched += 1
        _log(f"  fs {d.get('brand')} {d.get('name')} {d.get('size')}: ${offer['price']:.2f} (was ${offer['was']:.2f}) {offer['matched']} / {offer.get('variation')}")
        _apply(d, offer)
    dupe_matched = 0
    for d in dupes or []:
        if not d.get("price") or not d.get("size"):
            continue
        offer = lookup(client, dupe_as_deal(d))
        if not offer:
            _log(f"  fs dupe miss {d.get('dupe')} {d.get('size')}")
            continue
        dupe_matched += 1
        _log(f"  fs dupe {d.get('dupe')} {d.get('size')}: ${offer['price']:.2f} (was ${offer['was']:.2f}) {offer['matched']}")
        _apply(d, offer)
    _log(f"fragranceshop: {matched}/{len(deals)} deals and {dupe_matched} dupes priced, {client.transient}/{client.total} fetch failures")
    return matched


def _apply(d, offer):
    """Point the deal at the buy-button store and keep the other store as also-at.

    The lower price wins, except when the two affiliate prices are within 5%.
    Then the higher-commission store is the buy button. See scripts/merchants.py.
    """
    import merchants
    ours = {
        "retailer": d.get("retailer") or "Perfumania",
        "price": d.get("price"),
        "was": d.get("was"),
        "url": d.get("url"),
        "in_stock": True,
        "checked": d.get("checked"),
    }
    if ours["price"] is None or not ours["url"]:
        primary, other = offer, None
    else:
        chosen = merchants.prefer([
            {"retailer": ours["retailer"], "price": ours["price"], "url": ours["url"], "_src": ours},
            {"retailer": offer["retailer"], "price": offer["price"], "url": offer["url"], "_src": offer},
        ])
        primary = chosen["_src"] if chosen else ours
        other = offer if primary is ours else ours
    comps = [c for c in (d.get("comps") or []) if c.get("retailer") not in (RETAILER, ours["retailer"])]
    # rebuild comps from the two live affiliate offers plus any third-party reference (Ulta, etc.)
    base = []
    for src in (ours, offer):
        if src.get("price") is None or not src.get("url"):
            continue
        base.append({
            "retailer": src["retailer"],
            "price": src["price"],
            "url": src["url"],
            "checked": src.get("checked") or d.get("checked"),
        })
    d["comps"] = base + comps
    d["price"] = round(float(primary["price"]), 2)
    d["retailer"] = primary["retailer"]
    d["url"] = primary["url"]
    # "was" stays the selling store's own compare-at, never a guessed number
    was = primary.get("was")
    if was and float(was) > float(primary["price"]):
        d["was"] = round(float(was), 2)
        if primary["retailer"] == RETAILER:
            d.pop("was_label", None)
        d["pct_off"] = round((1 - float(d["price"]) / float(d["was"])) * 100)
    # If the store's own compare-at is under 15% off, fall back to the highest price another authorized,
    # non-affiliate retailer charges for the same bottle (e.g. Ulta via Muse.ai), labeled as such.
    # refresh.py drops anything still under 15%.
    if (d.get("pct_off") or 0) < 15:
        refs = [c for c in comps if c.get("price") and float(c["price"]) > d["price"]]
        if refs:
            ref = max(refs, key=lambda c: float(c["price"]))
            pct = round((1 - d["price"] / float(ref["price"])) * 100)
            if pct > (d.get("pct_off") or 0):
                d["was"], d["was_label"], d["pct_off"] = round(float(ref["price"]), 2), ref["retailer"], pct
    if other and other.get("price") is not None:
        d["also"] = {
            "retailer": other["retailer"],
            "price": round(float(other["price"]), 2),
            "url": other["url"],
        }
    d["fs"] = {
        "price": offer["price"],
        "was": offer["was"],
        "url": offer["url"],
        "name": offer.get("matched") or offer.get("name"),
        "variation": offer.get("variation"),
    }


if __name__ == "__main__":
    # manual check: python3 scripts/fragranceshop.py 'Calvin Klein' 'Free Cologne' '3.4 oz.' 'Eau De Toilette' men
    brand, name, size, typ, gender = sys.argv[1:6]
    deal = {"brand": brand, "name": name, "size": size, "type": typ, "gender": gender, "id": name}
    c = Client()
    print(json.dumps(lookup(c, deal), indent=2))
