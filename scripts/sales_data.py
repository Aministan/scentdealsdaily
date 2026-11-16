#!/usr/bin/env python3
"""Public bestseller, Le Male, and gift-set rows for the sales pages.

Reads FragranceShop's public Store API and FragranceNet's public product
listing pages. Never requests an affiliate click URL. A price is stored only
when that page or variation payload printed it. A miss is left without a price.
"""
from __future__ import annotations

import datetime
import html as html_lib
import json
import os
import re
import sys
import urllib.parse

import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALES_PATH = os.path.join(ROOT, "data", "sales.json")
PINS_PATH = os.path.join(ROOT, "data", "pin_posts.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fragrancenet
import fragranceshop
import product_images

FS = "FragranceShop"
FN = "FragranceNet"
FS_BEST = "https://www.fragranceshop.com/wp-json/wc/store/v1/products?orderby=popularity&order=desc&per_page=24"
FS_SETS = "https://www.fragranceshop.com/wp-json/wc/store/v1/products?category=2304&per_page=24&orderby=popularity"
FN_BEST = "https://www.fragrancenet.com/boutiques/best-selling-perfumes"
FN_SETS = "https://www.fragrancenet.com/ni/fragrances?f=0!9i"
BANNED_NAME = re.compile(r"bright\s+crystal", re.I)
BANNED_HOST = ("amazon.", "ebay.", "walmart.", "perfumesamerica.", "nordstromrack.", "sephora.")
SPRAY_BLOCK = re.compile(
    r"tester|\bunboxed\b|un-boxed|without box|no box|\boil\b|roll-?on|deodorant|"
    r"lotion|\bbalm\b|shower|body cream|body wash|\bsoap\b|gift set|coffret|\bset\b|"
    r"\bsample\b|\bvial\b|decant|aftershave|after shave|after-shave|body spray|"
    r"hair mist|body mist|miniature|\bmini\b|\bsplash\b",
    re.I,
)


def _log(msg):
    print(msg, file=sys.stderr)


def now_stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _host_ok(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    if links.is_tracking_url(url) or links.is_internal_redirect(url):
        return False
    host = links.host_of(url) or ""
    if any(bad in host for bad in BANNED_HOST):
        return False
    return links.host_is(host, "fragranceshop.com") or links.host_is(host, "fragrancenet.com")


def _plain_name(text):
    text = html_lib.unescape(text or "")
    text = text.replace("&#038;", "&").replace("&#8217;", "'")
    return re.sub(r"\s+", " ", text).strip()


def _banned(text):
    return bool(BANNED_NAME.search(text or ""))


def _gender(text):
    t = (text or "").lower()
    if "unisex" in t:
        return "unisex"
    if "for women" in t or "women" in t or "pour femme" in t:
        return "women"
    if "for men" in t or re.search(r"\bmen\b", t) or "pour homme" in t:
        return "men"
    return "unisex"


def _brand_from(product, name):
    brands = product.get("brands") if isinstance(product, dict) else None
    if isinstance(brands, list) and brands:
        label = _plain_name((brands[0] or {}).get("name") or "")
        if label:
            return label
    return ""


def _image_of(product):
    images = product.get("images") if isinstance(product, dict) else None
    if not images:
        return ""
    src = (images[0] or {}).get("src") or ""
    if not src.startswith("https://") or links.is_tracking_url(src):
        return ""
    return src


def _pct(price, was):
    if price is None or was is None or was <= price:
        return None
    return round((1 - float(price) / float(was)) * 100)


def _row(store, rank, brand, name, size, typ, gender, price, was, url, image, checked):
    if _banned(f"{brand} {name}") or not _host_ok(url):
        return None
    row = {
        "store": store,
        "rank": rank,
        "brand": brand,
        "name": name,
        "size": size or "",
        "type": typ or "",
        "gender": gender or "unisex",
        "url": url.split("#")[0],
        "image": image or "",
        "checked": checked,
        "in_stock": True,
    }
    if isinstance(price, (int, float)) and not isinstance(price, bool):
        row["price"] = round(float(price), 2)
    if isinstance(was, (int, float)) and not isinstance(was, bool) and (row.get("price") is None or was >= row["price"]):
        row["was"] = round(float(was), 2)
    pct = _pct(row.get("price"), row.get("was"))
    if pct is not None:
        row["pct_off"] = pct
    return row


def _spray_offer(client, product):
    """Largest sealed spray near 3.4 oz. None when the payload has no such size."""
    cands = []
    for var in product.get("variations") or []:
        label = ""
        for attr in var.get("attributes") or []:
            if (attr.get("name") or "") == "size":
                label = attr.get("value") or ""
        shown = label.replace("-", " ")
        if SPRAY_BLOCK.search(shown):
            continue
        oz = fragranceshop.size_oz(shown)
        if oz is None or oz < 1.0 or oz > 8.5:
            continue
        cands.append((abs(oz - 3.4), -oz, int(var["id"]), shown, oz))
    if not cands:
        return None
    cands.sort()
    offer = fragranceshop.variation(client, cands[0][2])
    if not offer:
        return None
    oz = cands[0][4]
    size = f"{oz:.1f} oz.".replace(".0 oz.", " oz.") if oz != int(oz) else f"{int(oz)} oz."
    # Keep the variation label's ounces exactly as the API spelled them when they include a decimal.
    raw_oz = fragranceshop.size_oz(offer.get("variation") or "")
    if raw_oz is not None:
        size = ("%g oz." % raw_oz)
    return offer, size


def fetch_fs_bestsellers(client, checked, limit=15):
    data = client.get_json(FS_BEST)
    if not isinstance(data, list):
        _log("  ! fragranceshop bestseller list missing")
        return []
    rows = []
    for product in data:
        name = _plain_name(product.get("name") or "")
        if not name or _banned(name):
            continue
        permalink = (product.get("permalink") or "").split("?")[0]
        if not _host_ok(permalink):
            continue
        picked = _spray_offer(client, product)
        price = was = None
        size = ""
        url = permalink
        if picked:
            offer, size = picked
            price, was = offer.get("price"), offer.get("was")
            url = offer.get("url") or permalink
        brand = _brand_from(product, name)
        display = re.sub(r"\s+for\s+(men|women|unisex)$", "", name, flags=re.I).strip()
        row = _row(FS, len(rows) + 1, brand, display, size, "", _gender(name), price, was, url, _image_of(product), checked)
        if not row:
            continue
        rows.append(row)
        priced = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
        _log(f"  fs bestseller {row['rank']} {display} {size} {priced}")
        if len(rows) >= limit:
            break
    return rows


def _fn_listing_items(text):
    """Product cards on a FragranceNet listing, in page order. Brand hubs are skipped."""
    items = []
    seen = set()
    pattern = re.compile(
        r"\[([^\]]+)\]\((https://www\.fragrancenet\.com/(?:perfume|cologne|fragrances)/[^)\s]+)\)"
        r"\[([^\]]+)\]\((https://www\.fragrancenet\.com/(?:perfume|cologne)/[^)\s]+)\)"
    )
    # The reader sometimes drops the brand link. A single product link still counts.
    single = re.compile(
        r"\[([^\]]+)\]\((https://www\.fragrancenet\.com/(?:perfume|cologne|fragrances)/[^)\s]+)\)"
    )
    for brand, _burl, name, url in pattern.findall(text):
        url = url.split("#")[0]
        if url in seen or _banned(name) or "/fragrances/" in url:
            continue
        seen.add(url)
        items.append((_plain_name(brand), _plain_name(name), url))
    if len(items) >= 8:
        return items
    for name, url in single.findall(text):
        url = url.split("#")[0]
        if url in seen or _banned(name):
            continue
        parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
        # /fragrances/<brand> is a brand hub. A product has the name and the concentration.
        if parts and parts[0] == "fragrances" and len(parts) < 4:
            continue
        if name.lower() in ("shop now", "learn more", "join now"):
            continue
        seen.add(url)
        items.append(("", _plain_name(name), url))
    return items


def _fn_text(url):
    status, body = fragrancenet.fetch_text(url)
    if status != "ok":
        _log(f"  ! fragrancenet listing {status} {url}")
        return ""
    if body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            content = (inner or {}).get("content") or ""
            if content:
                return content
    return fragrancenet.plain_text(body)


def _fn_price(url, checked):
    """One sealed size from the product page. Price stays empty when the page has none."""
    status, body = fragrancenet.fetch_text(url)
    if status != "ok":
        return None
    parsed = fragrancenet.parse_page(body, url)
    if not parsed:
        return None
    variants = [v for v in parsed.get("variants") or [] if not v.get("blocked") and v.get("price")]
    sprays = [v for v in variants if 1.0 <= float(v["oz"]) <= 8.5]
    pool = sprays or variants
    if not pool:
        if parsed.get("price"):
            return {"price": parsed["price"], "was": parsed.get("was"), "size": f"{parsed.get('heading_oz')} oz"}
        return None
    pool.sort(key=lambda v: (abs(float(v["oz"]) - 3.4), -float(v["oz"])))
    chosen = pool[0]
    was = parsed.get("was") if abs(float(chosen["oz"]) - float(parsed.get("heading_oz") or -1)) < 0.02 else None
    # A size row's own price was printed. The page retail applies only to the heading size.
    price = float(chosen["price"])
    if was is not None and was < price:
        was = None
    oz = float(chosen["oz"])
    size = "%g oz" % oz
    return {"price": price, "was": was, "size": size, "in_stock": parsed.get("in_stock", True)}


def fetch_fn_bestsellers(checked, limit=15):
    text = _fn_text(FN_BEST)
    items = _fn_listing_items(text)
    rows = []
    for brand, name, url in items:
        if _banned(f"{brand} {name}"):
            continue
        priced = _fn_price(url, checked)
        price = was = None
        size = ""
        if priced:
            price, was, size = priced.get("price"), priced.get("was"), priced.get("size") or ""
        image = ""
        row = _row(FN, len(rows) + 1, brand, name, size, "", _gender(name + " " + url), price, was, url, image, checked)
        if not row:
            continue
        if priced and priced.get("in_stock") is False:
            row["in_stock"] = False
        rows.append(row)
        bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
        _log(f"  fn bestseller {row['rank']} {brand} {name} {size} {bit}")
        if len(rows) >= limit:
            break
    return rows


def _fs_set_row(product, checked, rank):
    name = _plain_name(product.get("name") or "")
    if not re.search(r"\bgift\s+set\b|\bset\b", name, re.I):
        return None
    if re.search(r"tester|unboxed|\boil\b", name, re.I) or _banned(name):
        return None
    url = (product.get("permalink") or "").split("?")[0]
    if not _host_ok(url):
        return None
    price, was = fragranceshop.money(product.get("prices") or {})
    # A price range is more than one SKU. Do not treat the minimum as the set price.
    prices = product.get("prices") or {}
    span = (prices.get("price_range") or {})
    if span.get("min_amount") and span.get("max_amount") and span.get("min_amount") != span.get("max_amount"):
        price = was = None
    brand = _brand_from(product, name)
    display = re.sub(r"\s+for\s+(men|women|unisex)$", "", name, flags=re.I).strip()
    return _row(FS, rank, brand, display, "Gift set", "Gift Set", _gender(name), price, was, url, _image_of(product), checked)


def fetch_fs_sets(client, checked, limit=12):
    data = client.get_json(FS_SETS)
    if not isinstance(data, list):
        _log("  ! fragranceshop gift-set list missing")
        return []
    rows = []
    for product in data:
        row = _fs_set_row(product, checked, len(rows) + 1)
        if not row:
            continue
        rows.append(row)
        bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
        _log(f"  fs set {row['name']} {bit}")
        if len(rows) >= limit:
            break
    return rows


def fetch_fn_sets(checked, limit=12):
    text = _fn_text(FN_SETS)
    items = _fn_listing_items(text)
    rows = []
    for brand, name, url in items:
        blob = f"{brand} {name} {url}"
        if not re.search(r"gift\s*set|coffret|piece set", blob, re.I):
            continue
        if _banned(blob) or re.search(r"tester|unboxed|\bmini\b|0\.17", blob, re.I):
            continue
        priced = _fn_price(url, checked)
        price = was = None
        if priced:
            price, was = priced.get("price"), priced.get("was")
        row = _row(FN, len(rows) + 1, brand, name, "Gift set", "Gift Set", _gender(blob), price, was, url, "", checked)
        if not row:
            continue
        rows.append(row)
        bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
        _log(f"  fn set {brand} {name} {bit}")
        if len(rows) >= limit:
            break
    return rows


def _fs_search_rows(client, query, checked):
    found = []
    for product in fragranceshop.search(client, query) or []:
        if not isinstance(product, dict):
            continue
        name = _plain_name(product.get("name") or "")
        if _banned(name):
            continue
        permalink = (product.get("permalink") or "").split("?")[0]
        if not _host_ok(permalink):
            continue
        if re.search(r"\bset\b", name, re.I):
            row = _fs_set_row(product, checked, 0)
            if row:
                found.append(row)
            continue
        picked = _spray_offer(client, product)
        price = was = None
        size = ""
        url = permalink
        if picked:
            offer, size = picked
            price, was = offer.get("price"), offer.get("was")
            url = offer.get("url") or permalink
        brand = _brand_from(product, name) or "Jean Paul Gaultier"
        display = re.sub(r"\s+for\s+(men|women|unisex)$", "", name, flags=re.I).strip()
        row = _row(FS, 0, brand, display, size, "", _gender(name), price, was, url, _image_of(product), checked)
        if row:
            found.append(row)
    return found


def _le_male_key(row):
    """Only the names the store printed. Paradise Garden is not Le Beau Le Parfum."""
    blob = f"{row.get('name','')} {row.get('url','')}".lower().replace("-", " ")
    if "le beau le parfum" in blob:
        return "le beau le parfum"
    if "le beau" in blob:
        return "le beau"
    if "ultra male" in blob:
        return ""
    if "elixir" in blob and "le male" in blob:
        return "elixir"
    if "le male le parfum" in blob or "le parfum" in blob:
        return "le male le parfum"
    if re.search(r"\ble male\b", blob) and "le beau" not in blob:
        return "le male edt"
    if re.search(r"\bgift set\b|\bpiece set\b", blob):
        return "gift set"
    return ""


LE_MALE_ORDER = (
    "le male le parfum",
    "elixir",
    "le beau",
    "le beau le parfum",
    "le male edt",
    "gift set",
)


def fetch_le_male(client, checked):
    rows = []
    for query in ("Le Male", "Le Beau", "Le Male gift set", "Jean Paul Gaultier gift set"):
        rows.extend(_fs_search_rows(client, query, checked))
    fn_urls = [
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-male-le-parfum/eau-de-parfum",
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-male-elixir/parfum",
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-beau/edt",
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-beau-le-parfum/eau-de-parfum",
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-male/edt",
        "https://www.fragrancenet.com/cologne/jean-paul-gaultier/le-male/gift-set",
    ]
    for url in fn_urls:
        priced = _fn_price(url, checked)
        if not priced and url.endswith("/gift-set"):
            continue
        name = url.rstrip("/").split("/")[-2].replace("-", " ").title()
        if url.endswith("/edt") or url.endswith("/parfum") or "eau-de" in url:
            name = url.rstrip("/").split("/")[-2].replace("-", " ").title()
        price = was = None
        size = ""
        if priced:
            price, was, size = priced.get("price"), priced.get("was"), priced.get("size") or ""
        kind = "Gift Set" if "gift" in url else ""
        row = _row(FN, 0, "Jean Paul Gaultier", name, size or ("Gift set" if kind else ""), kind, "men", price, was, url, "", checked)
        if row and priced:
            rows.append(row)
        elif row and not url.endswith("/gift-set"):
            # The URL 404s inside _fn_price. Only keep a row when the page parsed.
            pass
    picked = []
    seen = set()
    for key in LE_MALE_ORDER:
        matches = [r for r in rows if _le_male_key(r) == key]
        if key != "gift set":
            # Prefer a priced FragranceShop row, then any priced row.
            matches.sort(key=lambda r: (r.get("price") is None, r.get("store") != FS))
            if not matches:
                _log(f"  le male missing {key}")
                continue
            row = matches[0]
            ident = (key, row.get("url"))
            if ident in seen:
                continue
            seen.add(ident)
            row = dict(row)
            row["role"] = key
            picked.append(row)
            bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
            _log(f"  le male {key}: {row['store']} {row['name']} {row.get('size')} {bit}")
            continue
        for row in matches:
            ident = row.get("url")
            if ident in seen:
                continue
            seen.add(ident)
            row = dict(row)
            row["role"] = key
            picked.append(row)
            bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
            _log(f"  le male set: {row['store']} {row['name']} {bit}")
    return picked


def _savings(row):
    price, was = row.get("price"), row.get("was")
    if isinstance(price, (int, float)) and isinstance(was, (int, float)) and was > price:
        return round(was - price, 2)
    return None


def _pin_record(title, page, image, kind):
    return {"title": title, "page": page, "image": image, "kind": kind}


def build_pin_posts(sales):
    """The list the Pinterest posts routine reads. Field: data/pin_posts.json posts[]."""
    posts = []
    posts.append(_pin_record(
        "Jean Paul Gaultier Le Male Le Parfum",
        "/fragrance/jean-paul-gaultier-le-male-le-parfum-cologne/",
        "/media/products/jean-paul-gaultier-le-male-le-parfum-cologne.jpg",
        "product",
    ))
    posts.append(_pin_record(
        "Fragrance gift sets",
        "/fragrance-gift-sets/",
        "",
        "page",
    ))
    posts.append(_pin_record(
        "Best sellers",
        "/best-sellers/",
        "",
        "page",
    ))
    top = []
    for row in (sales.get("bestsellers") or {}).get("fragranceshop") or []:
        if _banned(f"{row.get('brand','')} {row.get('name','')}"):
            continue
        top.append(row)
        if len(top) >= 5:
            break
    for row in top:
        slug = _slug(f"{row.get('brand') or ''} {row.get('name') or ''}")
        posts.append(_pin_record(
            f"{row.get('brand') or ''} {row.get('name') or ''}".strip(),
            f"/fragrance/{slug}/",
            f"/media/products/{slug}.jpg",
            "bestseller",
        ))
    # Page pins reuse the first product photo already hosted for that section.
    if top:
        slug = _slug(f"{top[0].get('brand') or ''} {top[0].get('name') or ''}")
        posts[2]["image"] = f"/media/products/{slug}.jpg"
    sets = sales.get("gift_sets") or []
    if sets:
        lead = sets[0]
        slug = _slug(f"{lead.get('brand') or ''} {lead.get('name') or ''}")
        posts[1]["image"] = f"/media/products/{slug}.jpg"
    return posts


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _cache_images(rows):
    dest = os.path.join(ROOT, "site", "media", "products")
    os.makedirs(dest, exist_ok=True)
    saved = 0
    for row in rows:
        slug = _slug(f"{row.get('brand') or ''} {row.get('name') or ''}")
        if not slug:
            continue
        path = os.path.join(dest, f"{slug}.jpg")
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            continue
        url = row.get("image") or ""
        if not url or links.is_tracking_url(url) or links.is_internal_redirect(url):
            continue
        try:
            jpeg = product_images._to_jpeg(product_images._fetch(url))
        except Exception as exc:
            _log(f"  ! image {slug}: {exc}")
            continue
        tmp = path + ".tmp"
        with open(tmp, "wb") as handle:
            handle.write(jpeg)
        os.replace(tmp, path)
        saved += 1
        _log(f"  image saved {slug}.jpg")
    return saved


def fetch_named_sets(client, checked):
    """Boxed sets whose slugs we already saw on the public catalog. Price comes from that product."""
    slugs = (
        "jean-paul-gaultier-for-women-3-piece-set",
        "jean-paul-gaultier-for-women-2-piece-set-3",
    )
    rows = []
    for slug in slugs:
        data = client.get_json(fragranceshop.API + "?slug=" + slug)
        product = data[0] if isinstance(data, list) and data else None
        if not isinstance(product, dict):
            continue
        row = _fs_set_row(product, checked, len(rows) + 1)
        if row:
            rows.append(row)
            bit = f"${row['price']:.2f}" if row.get("price") is not None else "no price"
            _log(f"  named set {row['name']} {bit}")
    return rows


def collect(checked=None):
    checked = checked or now_stamp()
    client = fragranceshop.Client()
    _log("sales data: FragranceShop bestsellers")
    fs_best = fetch_fs_bestsellers(client, checked)
    _log("sales data: FragranceNet bestsellers")
    fn_best = fetch_fn_bestsellers(checked)
    _log("sales data: gift sets")
    sets = fetch_fs_sets(client, checked) + fetch_named_sets(client, checked) + fetch_fn_sets(checked)
    seen_urls = set()
    unique = []
    for row in sets:
        key = (row.get("url") or "").split("?")[0]
        if key in seen_urls:
            continue
        seen_urls.add(key)
        unique.append(row)
    sets = unique
    # Highest dollar savings first. A set with no compare-at stays at the end, still listed.
    sets.sort(key=lambda r: (-(_savings(r) or -1), r.get("price") if r.get("price") is not None else 10**9, r.get("name") or ""))
    for i, row in enumerate(sets, 1):
        row["rank"] = i
        if _savings(row) is not None:
            row["savings"] = _savings(row)
    _log("sales data: Le Male family")
    family = fetch_le_male(client, checked)
    sales = {
        "updated": checked,
        "source": {
            "fragranceshop": FS_BEST.split("?")[0] + " orderby=popularity",
            "fragrancenet": FN_BEST,
        },
        "bestsellers": {"fragranceshop": fs_best, "fragrancenet": fn_best},
        "le_male": family,
        "gift_sets": sets,
    }
    return sales


def write_out(sales):
    posts = build_pin_posts(sales)
    sales["pin_posts_file"] = "data/pin_posts.json"
    sales["pin_posts_field"] = "posts"
    json.dump(sales, open(SALES_PATH, "w"), indent=1)
    json.dump({
        "updated": sales.get("updated"),
        "note": "Daily Pinterest posts read posts[]. Page images are site-hosted /media/products/{slug}.jpg files. FragranceShop CDN urls are not used.",
        "posts": posts,
    }, open(PINS_PATH, "w"), indent=1)
    image_rows = []
    image_rows.extend((sales.get("bestsellers") or {}).get("fragranceshop") or [])
    image_rows.extend((sales.get("bestsellers") or {}).get("fragrancenet") or [])
    image_rows.extend(sales.get("gift_sets") or [])
    image_rows.extend(sales.get("le_male") or [])
    saved = _cache_images(image_rows)
    _log(f"sales data wrote {SALES_PATH} and {PINS_PATH}; {saved} new images")
    return posts


def update(checked=None):
    """Refresh sales.json. On a hard failure, leave the previous file in place."""
    try:
        sales = collect(checked)
    except Exception as exc:
        _log(f"sales data fetch failed; keeping the previous file ({exc})")
        return None
    fs_n = len((sales.get("bestsellers") or {}).get("fragranceshop") or [])
    fn_n = len((sales.get("bestsellers") or {}).get("fragrancenet") or [])
    if (fs_n < 8 or fn_n < 8) and os.path.exists(SALES_PATH):
        _log(f"sales data too thin ({fs_n} FragranceShop, {fn_n} FragranceNet); keeping the previous file")
        return None
    return write_out(sales)


if __name__ == "__main__":
    update()
