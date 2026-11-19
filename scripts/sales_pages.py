#!/usr/bin/env python3
"""Best sellers, the Le Male family, gift sets, and today's largest price gaps.

Prices come from data/sales.json (read off public store pages) or from the
deal and gift rows the daily refresh already stored. Nothing here invents a
price, a rating, or a bottle the stores did not return.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse

import links

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALES_PATH = os.path.join(ROOT, "data", "sales.json")
PINS_PATH = os.path.join(ROOT, "data", "pin_posts.json")
MARK = "<!--sales-push-->"
FAMILY_HREF = "/jean-paul-gaultier-le-male-deals/"
BEST_HREF = "/best-sellers/"
SETS_HREF = "/fragrance-gift-sets/"
BANNED = re.compile(r"bright\s+crystal", re.I)


def _banned(row):
    blob = f"{row.get('brand') or ''} {row.get('name') or ''} {row.get('url') or ''}"
    if BANNED.search(blob):
        return True
    host = links.host_of(row.get("url") or "") or ""
    return any(bad in host for bad in ("amazon.", "ebay.", "walmart.", "perfumesamerica.", "nordstromrack.", "sephora."))


def _money(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), 2)


def _oz(size):
    match = re.search(r"([0-9]*\.?[0-9]+)", size or "")
    return float(match.group(1)) if match else None


def _path(url):
    return urllib.parse.urlparse((url or "").split("#")[0]).path.rstrip("/")


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _label(row):
    brand = (row.get("brand") or "").strip()
    name = (row.get("name") or "").strip()
    if brand and name.lower().startswith(brand.lower()):
        return name
    if brand and name:
        return f"{brand} {name}"
    return name or brand or "Fragrance"


def load_sales():
    if not os.path.isfile(SALES_PATH):
        return {}
    data = json.load(open(SALES_PATH, encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _deal_slug(ns, deal):
    return ns["frag_slug"](deal)


def match_deal(row, deals):
    """An existing deal for this exact store URL and size. A different size stays unmatched."""
    url = (row.get("url") or "").split("#")[0]
    path = _path(url)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    size_attr = (query.get("attribute_pa_size") or [""])[0]
    hits = []
    for deal in deals:
        deal_url = (deal.get("url") or "").split("#")[0]
        if size_attr:
            if size_attr in deal_url and _path(deal_url) == path:
                hits.append(deal)
            continue
        if deal_url.rstrip("/") == url.rstrip("/") or _path(deal_url) == path:
            hits.append(deal)
    if size_attr:
        return hits[0] if hits else None
    want = _oz(row.get("size"))
    if want is not None and len(hits) > 1:
        sized = [d for d in hits if _oz(d.get("size")) is not None and abs(_oz(d.get("size")) - want) < 0.05]
        if len(sized) == 1:
            return sized[0]
        return None
    if len(hits) == 1:
        return hits[0]
    return None


def _page_for(ns, row, deals, taken):
    """Internal path for a bestseller. Existing deal pages win. A new size gets its own path."""
    deal = match_deal(row, deals)
    if deal is not None:
        return f"/fragrance/{_deal_slug(ns, deal)}/", deal, False
    label = _label(row)
    base = _slug(label)
    if base in taken:
        base = _slug(f"{label} {row.get('size') or ''}")
    if not base or base in taken:
        return "", None, False
    return f"/fragrance/{base}/", None, True


def _price_bits(row):
    price = _money(row.get("price"))
    was = _money(row.get("was"))
    if price is None:
        return "Price not listed for a sealed spray on the store page.", None, None
    text = f"${price:.2f}"
    if was is not None and was > price:
        text += f" <span class='was'>${was:.2f}</span>"
    return text, price, was


def _buy(ns, row):
    url = row.get("url") or ""
    if not url or _banned(row):
        return ""
    store = row.get("store") or row.get("retailer") or "the store"
    product = ns["product_slug_for_url"](url) or _slug(_label(row))
    return ns["ext_a"](url, f"Buy at {ns['e'](store)}", cls="btn", placement="grid", product=product)


def _img(ns, row):
    slug = _slug(f"{row.get('brand') or ''} {row.get('name') or ''}")
    src = ns["hosted_photo_slug"](slug, row.get("image") or "")
    if not src:
        src = ns["PLACEHOLDER_SRC"]
    alt = _label(row)
    return f'<img loading="lazy" decoding="async" src="{ns["e"](src)}" alt="{ns["e"](alt)}" width="400" height="400">'


def _offer_ld(row):
    price = _money(row.get("price"))
    if price is None or not row.get("url") or not row.get("store"):
        return None
    return {
        "@type": "Offer",
        "price": f"{price:.2f}",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock" if row.get("in_stock") is not False else "https://schema.org/OutOfStock",
        "url": links.retailer_url(row["url"]) or row["url"],
        "seller": {"@type": "Organization", "name": row["store"]},
        "priceValidUntil": None,
    }


def _list_ld(name, rows, ns=None):
    items = []
    for i, row in enumerate(rows, 1):
        offer = _offer_ld(row)
        if not offer:
            continue
        offer["priceValidUntil"] = row.get("_until") or ""
        product = {"@type": "Product", "name": f"{_label(row)} {row.get('size') or ''}".strip()}
        if row.get("brand"):
            product["brand"] = {"@type": "Brand", "name": row["brand"]}
        if ns:
            slug = _slug(f"{row.get('brand') or ''} {row.get('name') or ''}")
            local = ns["hosted_photo_slug"](slug, row.get("image") or "")
            if local:
                product["image"] = ns["BASE"] + ns["PREFIX"] + local
        product["offers"] = {
            "@type": "AggregateOffer",
            "lowPrice": offer["price"],
            "highPrice": offer["price"],
            "offerCount": 1,
            "priceCurrency": "USD",
            "offers": [offer],
        }
        items.append({"@type": "ListItem", "position": len(items) + 1, "item": product})
    if not items:
        return None
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "itemListElement": items}


def _savings(row):
    price, was = _money(row.get("price")), _money(row.get("was"))
    if price is None or was is None or was <= price:
        return None
    return round(was - price, 2)


def gift_rows(ns, sales):
    rows = []
    seen = set()
    def add(row):
        if not isinstance(row, dict) or _banned(row):
            return
        store = row.get("store") or row.get("retailer") or ""
        if store not in ("FragranceShop", "FragranceNet"):
            return
        name_blob = f"{row.get('name') or ''} {row.get('type') or ''} {row.get('kind') or ''}"
        blob = f"{name_blob} {row.get('url') or ''}"
        if row.get("kind") != "set" and not re.search(r"gift\s*set|piece set|coffret|\bset\b", name_blob, re.I):
            return
        if re.search(r"tester|unboxed|\bmini\b|0\.17", blob, re.I):
            return
        key = _path(row.get("url"))
        if not key or key in seen:
            return
        seen.add(key)
        item = dict(row)
        item["store"] = store
        save = _savings(item)
        if save is not None:
            item["savings"] = save
        rows.append(item)
    for row in sales.get("gift_sets") or []:
        add(row)
    for row in ns["D"].get("gifts") or []:
        add(row)
    rows.sort(key=lambda r: (-(r.get("savings") if r.get("savings") is not None else -1), _money(r.get("price")) if _money(r.get("price")) is not None else 10**9, _label(r)))
    return rows


def _family_deals(ns):
    """Le Male Le Parfum first, then the other versions already in this price check."""
    deals = ns["deals"]
    order = (
        ("le male le parfum", lambda n: "le male le parfum" in n),
        ("elixir", lambda n: "le male" in n and "elixir" in n),
        ("le beau", lambda n: "le beau" in n and "paradise" not in n and "parfum" not in n),
        ("ultra male", lambda n: "ultra male" in n),
    )
    picked = []
    used = set()
    for _key, test in order:
        hits = []
        for deal in deals:
            if deal.get("id") in used:
                continue
            name = f"{deal.get('brand') or ''} {deal.get('name') or ''}".lower()
            if "jean paul" not in name and "gaultier" not in name and "le male" not in name and "le beau" not in name:
                continue
            if test(name):
                hits.append(deal)
        if not hits:
            continue
        hits.sort(key=lambda d: (d.get("retailer") != "FragranceShop", d.get("price") or 0))
        chosen = hits[0]
        used.add(chosen.get("id"))
        picked.append(chosen)
    return picked


def _row_html(ns, row, href):
    price_html, _price, _was = _price_bits(row)
    size = row.get("size") or ""
    size_bit = f" · {ns['e'](size)}" if size else ""
    link = f"<a href='{ns['PREFIX']}{href}'>{ns['e'](_label(row))}</a>" if href else ns["e"](_label(row))
    save = _savings(row)
    save_bit = f" <span class='meta'>save ${save:.2f}</span>" if save is not None else ""
    return (
        "<article class='card'>"
        + _img(ns, row)
        + f"<div class='nm'>{link}{size_bit}</div>"
        + f"<div class='price'>{price_html}</div>{save_bit}"
        + f"<div class='meta'>at {ns['e'](row.get('store') or '')} · checked {ns['e'](ns['checked_h'](row.get('checked')))}</div>"
        + _buy(ns, row)
        + "</article>"
    )


def _new_deal_page(ns, row, href, taken):
    """A deal page for a bestseller that is not already in deals.json."""
    label = _label(row)
    price = _money(row.get("price"))
    was = _money(row.get("was"))
    size = row.get("size") or ""
    store = row.get("store") or ""
    when = ns["checked_h"](row.get("checked"))
    slug = href.strip("/").split("/")[-1]
    ns["use_sid"]("deal", slug)
    if price is None:
        title = ns["fit"]([f"{label}: Price Not Listed", f"{label} Best Seller", label])
        desc = ns["fit"]([
            f"{label} is on the {store} bestseller list. The store page did not list a price for a sealed spray. Checked {when}.",
            f"{label} is a {store} bestseller. The store page did not list a price for a sealed spray. Checked {when}.",
        ], 160)
        body = (
            f"<h1>{ns['e'](label)}</h1>"
            f"<p class='sub'>The store page did not list a price for a sealed spray. Checked {ns['e'](when)}.</p>"
            f"<p>{ns['e'](label)} is on the public {ns['e'](store)} bestseller list. "
            "We did not find a sealed-spray price on that product page, so this page does not show one.</p>"
            + _buy(ns, row)
            + f"<p><a href='{ns['PREFIX']}{BEST_HREF}'>All best sellers</a></p>"
        )
        ns["page"](href.strip("/") + "/index.html", title, desc, body, index=True, feed=False, image=ns["DEFAULT_SHARE"])
        taken.add(slug)
        return
    was_bit = f" The page also listed ${was:.2f}." if was is not None and was > price else ""
    title = ns["fit"]([
        f"{label} {size}: ${price:.2f}".strip(),
        f"{label}: ${price:.2f}",
        label,
    ])
    desc = ns["fit"]([
        f"{label} {size} is ${price:.2f} at {store}.{was_bit} Price read from the store page. Checked {when}.",
        f"{label} is ${price:.2f} at {store}. Price read from the public store page. Checked {when}.",
    ], 160)
    faqs = [(
        f"Where did the {label} price come from?",
        f"We read ${price:.2f}" + (f" for {size}" if size else "") + f" on the {store} product page. Checked {when}. This page does not add a rating.",
    )]
    row = dict(row)
    row["_until"] = ns["PRICE_UNTIL"]
    ld = _list_ld(label, [row], ns)
    body = (
        f"<h1>{ns['e'](label)} {ns['e'](size)}</h1>"
        f"<p class='sub'>Price read from {ns['e'](store)} · checked {ns['e'](when)}.</p>"
        f"<p><b class='price'>${price:.2f}</b>"
        + (f" <span class='was'>${was:.2f}</span>" if was is not None and was > price else "")
        + f" at {ns['e'](store)}</p>"
        + _buy(ns, row)
        + f"<div class='box'>{_img(ns, row)}<p>This bottle is on the public {ns['e'](store)} bestseller list. "
        "The price above is the sealed size we read on that product page. We did not invent a rating.</p></div>"
        + ns["faqhtml"](faqs)
        + f"<p><a href='{ns['PREFIX']}{BEST_HREF}'>All best sellers</a></p>"
    )
    rel = href.strip("/") + "/index.html"
    ns["page"](rel, title, desc, body, [ld, ns["faqld"](faqs)] if ld else [ns["faqld"](faqs)], feed=True, image=ns["DEFAULT_SHARE"])
    _attach_gift_guides(ns, rel, row)
    taken.add(slug)


def _attach_gift_guides(ns, rel, row):
    """The fragrance sitemap audit requires two or three gift-guide links on every /fragrance/ page."""
    by_slug = dict(ns["GIFT_SUBPAGES"])
    picks_by = {slug: picks for slug, _title, picks in ns["GIFT_PAGE_PICKS"]}
    dealish = {
        "id": rel,
        "brand": row.get("brand") or _label(row),
        "name": row.get("name") or _label(row),
        "gender": row.get("gender") or "unisex",
        "price": row.get("price"),
        "size": row.get("size") or "",
    }
    pairs = ns["fragrance_fallback_pairs"](dealish, by_slug, picks_by)
    if len(pairs) < 2:
        pairs = [(slug, by_slug[slug]) for slug in ("for-him", "for-her", "under-50") if slug in by_slug and picks_by.get(slug)]
    if len(pairs) > 3:
        pairs = pairs[:3]
    if len(pairs) < 2:
        raise SystemExit(f"{rel}: could not find two gift guides")
    section = ns["fragrance_gift_section"](ns["FRAGRANCE_GIFT_HEADING"], pairs)
    path = os.path.join(ns["OUT"], rel)
    text = open(path, encoding="utf-8").read()
    if text.count("</main>") != 1:
        raise SystemExit(f"{rel}: expected one main for the gift guides")
    open(path, "w", encoding="utf-8").write(text.replace("</main>", section + "</main>", 1))
    ns["FRAGRANCE_GIFT_LINKS"].append((rel, list(pairs), "fallback"))


def _section(ns, heading, rows, href, more):
    if not rows:
        return ""
    cards = []
    for row, path in rows:
        cards.append(_row_html(ns, row, path))
    more_html = f"<p><a href='{ns['PREFIX']}{href}'>{ns['e'](more)}</a></p>" if href else ""
    return f"<section class='box'><h2 style='margin-top:0'>{ns['e'](heading)}</h2><div class='grid'>{''.join(cards)}</div>{more_html}</section>"


def _price_drops(ns):
    rows = []
    for deal in ns["deals"]:
        price, was = _money(deal.get("price")), _money(deal.get("was"))
        if price is None or was is None or was <= price:
            continue
        rows.append(deal)
    rows.sort(key=lambda d: (-(d["was"] - d["price"]), d["price"], d.get("id") or ""))
    shown = rows[:8]
    if not shown:
        return ""
    bits = []
    for deal in shown:
        gap = deal["was"] - deal["price"]
        href = f"/fragrance/{_deal_slug(ns, deal)}/"
        bits.append(
            "<div class='fold-deal'>"
            f"<p class='lead-name'><a href='{ns['PREFIX']}{href}'><b>{ns['e'](ns['fullname'](deal))}</b></a>"
            f" · {ns['e'](ns['sz'](deal.get('size') or ''))}</p>"
            f"<p class='lead-price'><span class='price'>${deal['price']:.2f}</span> "
            f"<span class='was'>${deal['was']:.2f}</span> "
            f"<span class='meta'>${gap:.2f} below the compare-at price at {ns['e'](deal['retailer'])}</span></p>"
            "</div>"
        )
    return (
        "<section class='box' id='price-drops'><h2 style='margin-top:0'>Biggest price drops today</h2>"
        f"<p>The largest gap between today's checked price and the compare-at price stored by the daily refresh. Checked {ns['e'](ns['upd_h'])}.</p>"
        + "".join(bits) + "</section>"
    )


def _splice(ns, rel, href, label):
    path = os.path.join(ns["OUT"], rel)
    if not os.path.isfile(path):
        return
    text = open(path, encoding="utf-8").read()
    needle = f"href='{ns['PREFIX']}{href}'"
    if needle in text or f'href="{ns["PREFIX"]}{href}"' in text:
        return
    chip = f"<p class='chips'><a href='{ns['PREFIX']}{href}'>{ns['e'](label)}</a></p>"
    match = re.search(r"<p class='sub'>.*?</p>", text, re.S)
    if not match:
        return
    text = text[:match.end()] + chip + text[match.end():]
    open(path, "w", encoding="utf-8").write(text)


def _write_best(ns, groups, linked):
    ns["use_sid"]("best", "sellers")
    when = ns["upd_h"]
    priced = [row for row, _href, _new in linked if _money(row.get("price")) is not None]
    lo = min(priced, key=lambda r: r["price"]) if priced else None
    lo_bit = f"${lo['price']:.2f}" if lo else ""
    title = ns["fit"]([
        f"Best Sellers From {lo_bit}: Checked Store Lists" if lo_bit else "Best Sellers From the Store Lists",
        f"Best Sellers From {lo_bit}" if lo_bit else "Best Sellers",
        "Best Sellers",
    ])
    desc = ns["fit"]([
        f"Best sellers from FragranceShop and FragranceNet" + (f", from {lo_bit}" if lo_bit else "") + f". Prices were read on the store pages. Checked {when}.",
        f"Shop the public FragranceShop and FragranceNet bestseller lists" + (f" from {lo_bit}" if lo_bit else "") + f". Checked {when}.",
    ], 160)
    parts = [
        "<h1>Best sellers</h1>",
        f"<p class='sub'>Ranked the way FragranceShop and FragranceNet list them. Prices were read on those pages. Checked {ns['e'](when)}.</p>",
        "<p>A bottle with no sealed-spray price on the store page is listed without one. This page does not add ratings.</p>",
    ]
    parts.append(ns["fs_fold_html"](ns["deals"], (
        {"brand":"margiela","name_is":"replica jazz club","size":"3.4"},
        "le male le parfum",
    )))
    ld_rows = []
    for store, rows in groups:
        cards = []
        for row, href, _new in rows:
            cards.append(_row_html(ns, row, href))
            if _money(row.get("price")) is not None:
                item = dict(row)
                item["_until"] = ns["PRICE_UNTIL"]
                ld_rows.append(item)
        parts.append(f"<h2>{ns['e'](store)}</h2><div class='grid'>{''.join(cards)}</div>")
    parts.append(f"<p><a href='{ns['PREFIX']}{FAMILY_HREF}'>Jean Paul Gaultier Le Male deals</a> · <a href='{ns['PREFIX']}{SETS_HREF}'>Fragrance gift sets</a></p>")
    ns["use_sid"]("best", "sellers")
    ld = _list_ld("Best sellers", ld_rows, ns)
    ns["page"]("best-sellers/index.html", title, desc, "".join(parts), [ld] if ld else None, feed=False, image=ns["DEFAULT_SHARE"])
    print(f"best sellers: {sum(len(rows) for _s, rows in groups)} bottles, title {len(title)} chars")


def _write_family(ns, family, sets):
    ns["use_sid"]("best", "le-male")
    if not family:
        raise SystemExit("Le Male page: Le Male Le Parfum is not in today's deals")
    lead = family[0]
    when = ns["upd_h"]
    price = f"${lead['price']:.2f}"
    title = ns["fit"]([
        f"Le Male Deals: Le Parfum {price}",
        f"Le Male Le Parfum Deals: {price}",
        "Le Male Deals",
    ])
    desc = ns["fit"]([
        f"Jean Paul Gaultier Le Male Le Parfum is {price} ({ns['sz'](lead.get('size') or '')}) at {lead['retailer']}. Elixir, Le Beau, and the gift sets we priced. Checked {when}.",
        f"Le Male Le Parfum is {price} at {lead['retailer']}. Other Le Male bottles in this price check are listed under it. Checked {when}.",
    ], 160)
    bits = [
        "<h1>Jean Paul Gaultier Le Male deals</h1>",
        f"<p class='sub'>Le Male Le Parfum first. Prices checked {ns['e'](when)}.</p>",
        f"<p><b>{ns['e'](ns['fullname'](lead))}</b> · {ns['e'](ns['sz'](lead.get('size') or ''))} · <span class='price'>{price}</span> at {ns['e'](lead['retailer'])}</p>",
        ns["ext_a"](lead["url"], f"Buy at {ns['e'](lead['retailer'])}", cls="btn", placement="cta", product=_deal_slug(ns, lead)),
        "<h2>The rest of the line</h2><div class='grid'>",
    ]
    for deal in family:
        href = f"/fragrance/{_deal_slug(ns, deal)}/"
        bits.append(
            "<article class='card'>"
            + ns["card_img"](deal)
            + f"<div class='nm'><a href='{ns['PREFIX']}{href}'>{ns['e'](ns['fullname'](deal))}</a> · {ns['e'](ns['sz'](deal.get('size') or ''))}</div>"
            + f"<div><span class='price'>${deal['price']:.2f}</span> <span class='was'>${deal['was']:.2f}</span></div>"
            + f"<div class='meta'>at {ns['e'](deal['retailer'])}</div>"
            + ns["ext_a"](deal["url"], f"Buy at {ns['e'](deal['retailer'])}", cls="btn", placement="grid", product=_deal_slug(ns, deal))
            + "</article>"
        )
    bits.append("</div>")
    gaultier_sets = [r for r in sets if "gaultier" in _label(r).lower() or "gaultier" in (r.get("url") or "")]
    if gaultier_sets:
        bits.append("<h2>Gift sets in stock</h2><div class='grid'>")
        for row in gaultier_sets:
            bits.append(_row_html(ns, row, ""))
        bits.append("</div>")
    bits.append(
        "<p>Le Beau Le Parfum and the original Le Male eau de toilette were not on the FragranceShop or FragranceNet product pages this check read, so they are not priced here.</p>"
        f"<p><a href='{ns['PREFIX']}/men/'>Men's cologne deals</a> · "
        f"<a href='{ns['PREFIX']}/black-friday/'>Black Friday deals</a> · "
        f"<a href='{ns['PREFIX']}/cyber-monday-fragrance-deals/'>Cyber Monday deals</a></p>"
    )
    faqs = [(
        "Why is Le Male Le Parfum listed first?",
        f"It is the Jean Paul Gaultier bottle this site has sold. The checked price is {price} for {ns['sz'](lead.get('size') or '')} at {lead['retailer']}.",
    )]
    ns["use_sid"]("deal", "le-male")
    shown = [dict(d, store=d.get("retailer"), brand=d.get("brand"), name=d.get("name")) for d in family]
    for row in shown:
        row["_until"] = ns["PRICE_UNTIL"]
    ld = _list_ld("Jean Paul Gaultier Le Male deals", shown, ns)
    ns["page"]("jean-paul-gaultier-le-male-deals/index.html", title, desc, "".join(bits), [ld, ns["faqld"](faqs)] if ld else [ns["faqld"](faqs)], feed=False, image=ns["DEFAULT_SHARE"])
    print(f"le male family: {len(family)} bottles, {len(gaultier_sets)} gift sets, title {len(title)} chars")


def _write_sets(ns, sets):
    ns["use_sid"]("gifts", "sets")
    if len(sets) < 3:
        raise SystemExit(f"fragrance gift sets: only {len(sets)} FragranceShop or FragranceNet sets")
    priced = [r for r in sets if _money(r.get("price")) is not None]
    lo = min(priced, key=lambda r: r["price"])
    when = ns["upd_h"]
    title = ns["fit"]([
        f"Fragrance Gift Sets From ${lo['price']:.2f}",
        f"Gift Sets From ${lo['price']:.2f}",
        "Fragrance Gift Sets",
    ])
    desc = ns["fit"]([
        f"Fragrance gift sets from FragranceShop and FragranceNet, from ${lo['price']:.2f}. Sorted by savings when the store listed a compare-at price. Checked {when}.",
        f"Shop fragrance gift sets from ${lo['price']:.2f}. Prices were read from FragranceShop and FragranceNet. Checked {when}.",
    ], 160)
    cards = "".join(_row_html(ns, row, "") for row in sets)
    faqs = [(
        "How are these gift sets ordered?",
        "Sets with a compare-at price are sorted by the dollar gap between that price and the price we read. A set with no compare-at price stays at the end and still shows the price we read.",
    )]
    ld_rows = []
    for row in sets:
        if _money(row.get("price")) is None:
            continue
        item = dict(row)
        item["_until"] = ns["PRICE_UNTIL"]
        ld_rows.append(item)
    ld = _list_ld("Fragrance gift sets", ld_rows, ns)
    body = (
        "<h1>Fragrance gift sets</h1>"
        f"<p class='sub'>FragranceShop and FragranceNet sets, largest savings first. Checked {ns['e'](when)}.</p>"
        f"<div class='grid'>{cards}</div>"
        + ns["faqhtml"](faqs)
        + f"<p><a href='{ns['PREFIX']}{BEST_HREF}'>Best sellers</a> · <a href='{ns['PREFIX']}{FAMILY_HREF}'>Le Male deals</a></p>"
    )
    ns["use_sid"]("gifts", "sets")
    ns["page"]("fragrance-gift-sets/index.html", title, desc, body, [ld, ns["faqld"](faqs)] if ld else [ns["faqld"](faqs)], feed=False, image=ns["DEFAULT_SHARE"])
    print(f"gift sets: {len(sets)} sets, from ${lo['price']:.2f}, title {len(title)} chars")


def _sync_pins(ns, linked):
    """Point bestseller pins at the page this build actually wrote."""
    if not os.path.isfile(PINS_PATH):
        return
    data = json.load(open(PINS_PATH, encoding="utf-8"))
    by_label = {}
    for row, href, _new in linked:
        by_label[_slug(_label(row))] = href
    changed = False
    for post in data.get("posts") or []:
        if post.get("kind") != "bestseller":
            continue
        slug = (post.get("page") or "").strip("/").split("/")[-1]
        href = by_label.get(slug) or by_label.get(_slug(post.get("title") or ""))
        if not href:
            href = BEST_HREF
        if post.get("page") != href:
            post["page"] = href
            changed = True
        image = post.get("image") or ""
        if image and not image.startswith("/media/products/"):
            post["image"] = f"/media/products/{slug}.jpg"
            changed = True
    if changed:
        json.dump(data, open(PINS_PATH, "w"), indent=1)
        print("pin posts: bestseller page paths updated")


def build_pages(ns):
    sales = load_sales()
    deals = ns["deals"]
    taken = {_deal_slug(ns, d) for d in deals}
    linked = []
    groups = []
    best = sales.get("bestsellers") or {}
    added = 0
    for store_key, title in (("fragranceshop", "FragranceShop"), ("fragrancenet", "FragranceNet")):
        rows = []
        for row in best.get(store_key) or []:
            if _banned(row):
                raise SystemExit(f"bestseller list includes a banned product: {_label(row)}")
            if _money(row.get("price")) is None:
                continue
            href, _deal, is_new = _page_for(ns, row, deals, taken)
            if is_new and href:
                _new_deal_page(ns, row, href, taken)
                added += 1
            rows.append((row, href, is_new))
            linked.append((row, href, is_new))
        groups.append((title, rows))
    if sum(len(rows) for _t, rows in groups) < 10:
        raise SystemExit("best sellers: fewer than 10 store rows in data/sales.json")
    _write_best(ns, groups, linked)
    family = _family_deals(ns)
    sets = gift_rows(ns, sales)
    _write_family(ns, family, sets)
    _write_sets(ns, sets)
    home = os.path.join(ns["OUT"], "index.html")
    text = open(home, encoding="utf-8").read()
    if text.count(MARK) != 1:
        raise SystemExit("homepage is missing the sales section mark")
    # Keep this off article.card. The homepage audit requires every card to use the deal-grid price markup.
    best_bits = []
    for row, href, _new in linked:
        if not href or _money(row.get("price")) is None:
            continue
        best_bits.append(
            f"<li><a href='{ns['PREFIX']}{href}'>{ns['e'](_label(row))}</a> "
            f"· ${row['price']:.2f} at {ns['e'](row.get('store') or '')}</li>"
        )
        if len(best_bits) >= 6:
            break
    block = (
        "<section class='box'><h2 style='margin-top:0'>Best sellers</h2>"
        + f"<ol>{''.join(best_bits)}</ol>"
        + f"<p><a href='{ns['PREFIX']}{BEST_HREF}'>All best sellers</a></p></section>"
        + _price_drops(ns)
    )
    if family:
        lead = family[0]
        block += (
            "<section class='box'><h2 style='margin-top:0'>Jean Paul Gaultier Le Male</h2>"
            f"<p><a href='{ns['PREFIX']}{FAMILY_HREF}'>Le Male Le Parfum</a> is "
            f"${lead['price']:.2f} for {ns['e'](ns['sz'](lead.get('size') or ''))} at {ns['e'](lead['retailer'])}. "
            f"<a href='{ns['PREFIX']}{FAMILY_HREF}'>See the Le Male deals</a>.</p></section>"
        )
    if sets:
        lead = sets[0]
        price = _money(lead.get("price"))
        price_bit = f" from ${price:.2f}" if price is not None else ""
        block += (
            "<section class='box'><h2 style='margin-top:0'>Fragrance gift sets</h2>"
            f"<p><a href='{ns['PREFIX']}{SETS_HREF}'>Holiday gift sets</a>{price_bit} "
            "from FragranceShop and FragranceNet, largest savings first when the store listed a compare-at price.</p></section>"
        )
    open(home, "w", encoding="utf-8").write(text.replace(MARK, block, 1))
    _sync_pins(ns, linked)
    print(f"sales pages: {added} new deal pages")
    return added


def apply_links(ns):
    """Cologne, Black Friday, and Cyber Monday pages point at the Le Male family."""
    for rel in (
        "men/index.html",
        "black-friday/index.html",
        "black-friday-cologne-deals/index.html",
        "cyber-monday-fragrance-deals/index.html",
        "cyber-monday-cologne-deals/index.html",
        "brands/jean-paul-gaultier/index.html",
        "black-friday/jean-paul-gaultier/index.html",
    ):
        _splice(ns, rel, FAMILY_HREF, "Jean Paul Gaultier Le Male deals")
