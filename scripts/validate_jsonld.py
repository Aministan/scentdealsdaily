#!/usr/bin/env python3
"""Parse every built HTML page and check JSON-LD.

Deal and gift pages need an ItemList of Product with Offer. Each Offer must
carry price, priceCurrency USD, availability, and a seller name. Prices have
to be ones already stored in data/deals.json. AggregateRating is rejected
because this repo has no review data. BreadcrumbList is required on every
indexable page except the homepage. A visible FAQ section must match FAQPage.

Does not request any URL. Run after scripts/build.py.
"""
import json, os, re, sys, html, urllib.parse

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT, "site")
DEALS=os.path.join(ROOT, "data", "deals.json")
AVAIL={"https://schema.org/InStock","https://schema.org/OutOfStock",
       "http://schema.org/InStock","http://schema.org/OutOfStock"}
CTR_RELS=(
    "index.html",
    "men/index.html",
    "women/index.html",
    "unisex/index.html",
    "gifts/index.html",
    "gifts/for-him/index.html",
    "gifts/for-her/index.html",
    "gifts/under-50/index.html",
    "black-friday/index.html",
    "black-friday-fragrance-deals/index.html",
    "black-friday-cologne-deals/index.html",
    "black-friday-perfume-deals/index.html",
    "black-friday-fragrance-deals-under-30/index.html",
    "cyber-monday-fragrance-deals/index.html",
    "cyber-monday-cologne-deals/index.html",
    "cyber-monday-perfume-deals/index.html",
    "gifts/stocking-stuffers-for-men/index.html",
    "gifts/stocking-stuffers-for-her/index.html",
    "gifts/christmas-cologne-gifts-for-him/index.html",
    "gifts/christmas-perfume-gifts-for-her/index.html",
    "gifts/perfume-gifts-for-her-under-25/index.html",
    "gifts/christmas-cologne-gifts-under-100/index.html",
    "gifts/christmas-perfume-gifts-under-100/index.html",
    "gifts/black-friday-unisex-fragrance-deals/index.html",
    "gifts/cyber-monday-luxury-fragrance-deals/index.html",
)

def _money(value):
    if isinstance(value, bool) or value is None: return None
    if isinstance(value, (int, float)): return f"{float(value):.2f}"
    if isinstance(value, str) and re.fullmatch(r"\d+\.\d{2}", value): return value
    return None

def known_prices():
    data=json.load(open(DEALS, encoding="utf-8"))
    found=set()
    def take(row):
        if not isinstance(row, dict): return
        for key in ("price",):
            bit=_money(row.get(key))
            if bit: found.add(bit)
        for key in ("comps",):
            for comp in row.get(key) or []:
                bit=_money(comp.get("price") if isinstance(comp, dict) else None)
                if bit: found.add(bit)
        also=row.get("also")
        if isinstance(also, dict):
            bit=_money(also.get("price"))
            if bit: found.add(bit)
        for key in ("fs", "fn"):
            extra=row.get(key)
            if isinstance(extra, dict):
                bit=_money(extra.get("price"))
                if bit: found.add(bit)
    for row in data.get("deals") or []: take(row)
    for row in data.get("gifts") or []: take(row)
    for row in data.get("dupes") or []: take(row)
    return found

def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)

def types_of(node):
    raw=node.get("@type")
    if isinstance(raw, list): return {t for t in raw if isinstance(t, str)}
    if isinstance(raw, str): return {raw}
    return set()

def scripts(text):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)

def needs_itemlist(rel, text):
    if 'content="noindex' in text: return False
    if rel=="index.html" or rel in ("men/index.html","women/index.html","unisex/index.html"): return True
    if rel.startswith("fragrance/"): return True
    if rel.startswith("best/"): return True
    if rel.startswith("black-friday") or rel.startswith("cyber-monday"): return True
    if rel.startswith("gifts/") and '<article class="card">' in text: return True
    return False

def offer_errors(offer, prices, where):
    bad=[]
    if not isinstance(offer, dict):
        return [f"{where}: offer is not an object"]
    kind=types_of(offer)
    if "AggregateOffer" in kind:
        if offer.get("priceCurrency")!="USD":
            bad.append(f"{where}: AggregateOffer priceCurrency is not USD")
        nested=offer.get("offers") or []
        if not isinstance(nested, list) or not nested:
            bad.append(f"{where}: AggregateOffer has no nested Offers")
            return bad
        nested_prices=[]
        for i, child in enumerate(nested):
            bad.extend(offer_errors(child, prices, f"{where} offer {i+1}"))
            bit=_money(child.get("price") if isinstance(child, dict) else None)
            if bit: nested_prices.append(float(bit))
        for key in ("lowPrice","highPrice"):
            bit=_money(offer.get(key))
            if not bit:
                bad.append(f"{where}: AggregateOffer {key} missing")
            elif bit not in prices:
                bad.append(f"{where}: {key} {bit} is not a stored price")
        if nested_prices and _money(offer.get("lowPrice")) and _money(offer.get("highPrice")):
            if abs(float(_money(offer.get("lowPrice")))-min(nested_prices))>0.001 or abs(float(_money(offer.get("highPrice")))-max(nested_prices))>0.001:
                bad.append(f"{where}: AggregateOffer low/high does not match its Offers")
        return bad
    if "Offer" not in kind:
        bad.append(f"{where}: expected Offer, found {offer.get('@type')}")
        return bad
    price=_money(offer.get("price"))
    if not price:
        bad.append(f"{where}: Offer price missing")
    elif price not in prices:
        bad.append(f"{where}: Offer price {price} is not in deals.json")
    if offer.get("priceCurrency")!="USD":
        bad.append(f"{where}: Offer priceCurrency is not USD")
    if offer.get("availability") not in AVAIL:
        bad.append(f"{where}: Offer availability missing")
    seller=offer.get("seller")
    name=seller.get("name") if isinstance(seller, dict) else ""
    if not isinstance(name, str) or not name.strip():
        bad.append(f"{where}: Offer seller name missing")
    return bad

def faq_visible(text):
    blob=re.search(r"<h2 style='margin-top:0'>FAQ</h2>(.*?)</section>", text, re.S)
    if not blob: return None
    return [(html.unescape(q), html.unescape(a)) for q,a in re.findall(r"<h3>(.*?)</h3><p>(.*?)</p>", blob.group(1), re.S)]

def main():
    if not os.path.isdir(OUT):
        print("site/ is missing. Run scripts/build.py first.")
        return 1
    prices=known_prices()
    if not prices:
        print("deals.json has no prices")
        return 1
    bad=[]
    pages=0
    crumbs=0
    lists=0
    offers=0
    faqs=0
    ratings=0
    for dirpath, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"): continue
            path=os.path.join(dirpath, fn)
            rel=os.path.relpath(path, OUT).replace(os.sep, "/")
            text=open(path, encoding="utf-8").read()
            pages+=1
            blocks=[]
            for raw in scripts(text):
                try: blocks.append(json.loads(raw))
                except json.JSONDecodeError as ex:
                    bad.append(f"{rel}: JSON-LD did not parse ({ex})")
            nodes=[]
            for block in blocks:
                nodes.extend(walk(block))
            for node in nodes:
                if "AggregateRating" in types_of(node) or "Review" in types_of(node) or "aggregateRating" in node:
                    ratings+=1
                    bad.append(f"{rel}: AggregateRating or review markup without review data")
            noindex='content="noindex' in text
            canon_m=re.search(r'<link rel="canonical" href="([^"]*)"', text)
            canon_path=urllib.parse.urlparse(html.unescape(canon_m.group(1))).path if canon_m else ""
            if rel=="index.html":
                own_path="/"
            elif rel.endswith("/index.html"):
                own_path="/"+rel[:-len("index.html")]
            else:
                own_path="/"+rel
            # Aliases are noindex and canonicalize to a different guide. The homepage
            # and the 404 have no trail. A noindex page that is its own URL, such as
            # the subscribe confirmation, still has one.
            alias=noindex and canon_path.rstrip("/")!=own_path.rstrip("/")
            found=[n for n in nodes if "BreadcrumbList" in types_of(n)]
            if rel in ("index.html","404.html") or alias:
                if found: bad.append(f"{rel}: unexpected BreadcrumbList")
            else:
                crumbs+=1
                if len(found)!=1:
                    bad.append(f"{rel}: expected one BreadcrumbList, found {len(found)}")
                elif found[0].get("@context")!="https://schema.org":
                    bad.append(f"{rel}: BreadcrumbList missing @context")
            if needs_itemlist(rel, text):
                itemlists=[n for n in nodes if "ItemList" in types_of(n)]
                products=[]
                for itemlist in itemlists:
                    for el in itemlist.get("itemListElement") or []:
                        item=el.get("item") if isinstance(el, dict) else None
                        if isinstance(item, dict) and "Product" in types_of(item):
                            products.append(item)
                if not itemlists:
                    bad.append(f"{rel}: missing ItemList")
                elif not products:
                    bad.append(f"{rel}: ItemList has no Product")
                else:
                    lists+=1
                    for i, product in enumerate(products, 1):
                        offer=product.get("offers")
                        if not offer:
                            bad.append(f"{rel}: Product {i} has no Offer")
                            continue
                        errs=offer_errors(offer, prices, f"{rel} product {i}")
                        bad.extend(errs)
                        if not errs: offers+=1
            visible=faq_visible(text)
            if visible is not None:
                faqs+=1
                faq_nodes=[n for n in nodes if "FAQPage" in types_of(n)]
                if len(faq_nodes)!=1:
                    bad.append(f"{rel}: visible FAQ but {len(faq_nodes)} FAQPage blocks")
                else:
                    entities=faq_nodes[0].get("mainEntity") or []
                    pairs=[]
                    for q in entities:
                        if not isinstance(q, dict): continue
                        pairs.append((q.get("name"), (q.get("acceptedAnswer") or {}).get("text")))
                    if pairs!=visible:
                        bad.append(f"{rel}: FAQPage does not match the visible FAQ")
    ctr=[]
    for rel in CTR_RELS:
        fp=os.path.join(OUT, rel)
        if not os.path.isfile(fp):
            bad.append(f"{rel}: missing a priority page")
            continue
        text=open(fp, encoding="utf-8").read()
        title=html.unescape(re.search(r"<title>(.*?)</title>", text, re.S).group(1))
        desc=html.unescape(re.search(r'<meta name="description" content="([^"]*)"', text).group(1))
        lead=re.search(r"class='lead-price'>.*?<span class='price'>\$([0-9]+\.[0-9]{2})</span>", text, re.S)
        if len(title)>60:
            bad.append(f"{rel}: title is {len(title)} characters ({title})")
        if not lead:
            bad.append(f"{rel}: no lead price to put in the description")
        elif f"${lead.group(1)}" not in desc:
            bad.append(f"{rel}: description misses the lowest price ${lead.group(1)}")
        if not re.search(r"\b(Buy|Shop)\b", desc):
            bad.append(f"{rel}: description has no Buy or Shop call to action")
        ctr.append((rel, len(title), title, desc))
    if bad:
        print(f"JSON-LD check failed ({len(bad)} problems):")
        for line in bad[:50]:
            print(" ", line)
        return 1
    print(f"JSON-LD: {pages} pages, {crumbs} breadcrumbs, {lists} item lists, {offers} product offers, {faqs} FAQ pages, {ratings} ratings, {len(prices)} stored prices")
    print(f"CTR snippets: {len(ctr)} pages, titles <= 60, description has the lead price and a call to action")
    for rel, n, title, desc in ctr:
        print(f"  {rel}: {n} | {title}")
        print(f"    {desc}")
    return 0

if __name__=="__main__":
    sys.exit(main())
