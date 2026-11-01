"""Which approved store gets the buy button when one bottle is priced at two stores.

Rates already written down for this site:
- Perfumania, CJ, reported ~10% in docs/affiliate-programs.md (another listing says 3.2%).
- FragranceShop, CJ, 5% in docs/affiliate-programs.md.
- FragranceNet, Rakuten, 0.10%.

When the higher price is within 5% of the lower price, the higher-commission store
is the buy button. A wider gap keeps the lower price. Ulta and other compare-at
rows are not buy buttons. A switch that would put the deal under the 15% floor
against the stored compare-at is skipped.
"""
AFFILIATE_COMMISSION = {
    "Perfumania": 10.0,
    "FragranceShop": 5.0,
    "FragranceNet": 0.10,
}
# Higher price must be <= cheaper * (1 + CLOSE).
CLOSE = 0.05


def commission(retailer):
    return AFFILIATE_COMMISSION.get(retailer or "", 0.0)


def _price(offer):
    try:
        price = float(offer.get("price"))
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return price


def prefer(offers):
    """Return the offer dict that should be the buy button, or None.

    Non-affiliate rows are ignored. The returned object is one of the inputs.
    """
    rows = []
    for offer in offers or []:
        if not isinstance(offer, dict) or not offer.get("url"):
            continue
        if offer.get("retailer") not in AFFILIATE_COMMISSION:
            continue
        if _price(offer) is None:
            continue
        rows.append(offer)
    if not rows:
        return None
    cheapest = min(_price(offer) for offer in rows)
    cap = cheapest * (1 + CLOSE)
    band = [offer for offer in rows if _price(offer) <= cap + 1e-6]
    band.sort(key=lambda offer: (-commission(offer.get("retailer")), _price(offer), offer.get("retailer") or ""))
    return band[0]


def apply_deal(deal):
    """Point a deal at the preferred affiliate offer.

    Returns True when the buy button moves. Uses the compare-at already stored
    on the deal. Does not invent a price. Skips a move that would leave the
    deal under 15% off that compare-at.
    """
    if not isinstance(deal, dict):
        return False
    offers = []
    seen = set()

    def add(retailer, price, url, checked=None):
        if retailer not in AFFILIATE_COMMISSION or price is None or not url:
            return
        if retailer in seen:
            return
        seen.add(retailer)
        offers.append({"retailer": retailer, "price": price, "url": url, "checked": checked})

    add(deal.get("retailer"), deal.get("price"), deal.get("url"), deal.get("checked"))
    for comp in deal.get("comps") or []:
        if isinstance(comp, dict):
            add(comp.get("retailer"), comp.get("price"), comp.get("url"), comp.get("checked"))
    also = deal.get("also") if isinstance(deal.get("also"), dict) else {}
    add(also.get("retailer"), also.get("price"), also.get("url"))
    chosen = prefer(offers)
    if not chosen:
        return False
    current = _price(deal)
    if chosen.get("retailer") == deal.get("retailer") and current is not None and abs(_price(chosen) - current) < 0.009:
        return False
    was = deal.get("was")
    new_price = _price(chosen)
    if isinstance(was, (int, float)) and not isinstance(was, bool) and was > new_price:
        pct = round((1 - new_price / float(was)) * 100)
    else:
        pct = 0
    if pct < 15:
        return False
    previous = {"retailer": deal.get("retailer"), "price": deal.get("price"), "url": deal.get("url")}
    deal["retailer"] = chosen["retailer"]
    deal["price"] = round(new_price, 2)
    deal["url"] = chosen["url"]
    deal["pct_off"] = pct
    if chosen.get("checked"):
        deal["checked"] = chosen["checked"]
    if previous.get("url") and previous.get("retailer") != chosen["retailer"]:
        deal["also"] = {
            "retailer": previous["retailer"],
            "price": round(float(previous["price"]), 2),
            "url": previous["url"],
        }
    return True


def apply_rows(rows):
    return sum(1 for deal in (rows or []) if apply_deal(deal))


if __name__ == "__main__":
    cheap = {"retailer": "FragranceNet", "price": 40.00, "url": "https://www.fragrancenet.com/a"}
    close = {"retailer": "FragranceShop", "price": 41.50, "url": "https://www.fragranceshop.com/a"}
    far = {"retailer": "Perfumania", "price": 55.00, "url": "https://www.perfumania.com/a"}
    picked = prefer([cheap, close, far])
    if picked["retailer"] != "FragranceShop":
        raise SystemExit(f"close CJ store should win, got {picked['retailer']}")
    picked = prefer([cheap, far])
    if picked["retailer"] != "FragranceNet":
        raise SystemExit(f"wide gap should keep the lower price, got {picked['retailer']}")
    touch_fs = {"retailer": "FragranceShop", "price": 27.95, "url": "https://www.fragranceshop.com/b"}
    touch_pm = {"retailer": "Perfumania", "price": 29.99, "url": "https://www.perfumania.com/b"}
    picked = prefer([touch_fs, touch_pm])
    if picked["retailer"] != "FragranceShop":
        raise SystemExit("7.3% gap should stay on the cheaper store")
    print("merchants ok")
