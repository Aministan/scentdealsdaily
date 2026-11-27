#!/usr/bin/env python3
"""One checked price per SKU, merchant, and day.

The daily refresh appends rows to data/price-history.json. A second run on the
same day replaces that day's price instead of adding a duplicate. Rows older
than 400 days drop off. A missing or unreadable file starts empty. A SKU that
leaves the price check keeps its older rows and does not fail the refresh.
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "price-history.json")
CAP_DAYS = 400
MERCHANTS = ("FragranceShop", "Perfumania", "FragranceNet")
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:
    ET = datetime.timezone(datetime.timedelta(hours=-5))


def _price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        price = round(float(value), 2)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return price


def _day(value):
    text = str(value or "")[:10]
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return None
    return text


def sku_of(deal):
    if not isinstance(deal, dict):
        return None
    sku = deal.get("sku")
    if isinstance(sku, str) and sku.strip():
        return sku.strip()
    deal_id = deal.get("id")
    if isinstance(deal_id, str) and deal_id.strip():
        return deal_id.strip()
    return None


def offers_for(deal):
    """Approved-merchant prices already stored on the deal. Ulta stays off this file."""
    found = {}

    def add(merchant, price):
        if merchant not in MERCHANTS or merchant in found:
            return
        amount = _price(price)
        if amount is None:
            return
        found[merchant] = amount

    if isinstance(deal, dict):
        add(deal.get("retailer"), deal.get("price"))
        for comp in deal.get("comps") or []:
            if isinstance(comp, dict):
                add(comp.get("retailer"), comp.get("price"))
        also = deal.get("also") if isinstance(deal.get("also"), dict) else {}
        add(also.get("retailer"), also.get("price"))
    return found


def load(path=PATH):
    """Rows already on disk. Missing, unreadable, or the wrong shape is an empty list."""
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    if isinstance(raw, dict):
        raw = raw.get("rows")
    if not isinstance(raw, list):
        return []
    rows = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        sku = row.get("sku")
        merchant = row.get("merchant")
        day = _day(row.get("date"))
        price = _price(row.get("price"))
        if not isinstance(sku, str) or not sku.strip() or merchant not in MERCHANTS or not day or price is None:
            continue
        rows.append({"sku": sku.strip(), "merchant": merchant, "price": price, "date": day})
    return rows


def _date_of(now_iso):
    if isinstance(now_iso, str) and now_iso:
        try:
            stamp = datetime.datetime.strptime(now_iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
            return stamp.astimezone(ET).date().isoformat()
        except ValueError:
            day = _day(now_iso)
            if day:
                return day
    return datetime.datetime.now(ET).date().isoformat()


def record(deals, now_iso, path=PATH):
    """Append today's rows. Returns the row count. Never raises."""
    try:
        day = _date_of(now_iso)
        keyed = {}
        for row in load(path):
            keyed[(row["sku"], row["merchant"], row["date"])] = row
        for deal in deals or []:
            sku = sku_of(deal)
            if not sku:
                continue
            for merchant, price in offers_for(deal).items():
                keyed[(sku, merchant, day)] = {"sku": sku, "merchant": merchant, "price": price, "date": day}
        rows = list(keyed.values())
        dates = []
        for row in rows:
            try:
                dates.append(datetime.date.fromisoformat(row["date"]))
            except ValueError:
                continue
        if dates:
            cutoff = max(dates) - datetime.timedelta(days=CAP_DAYS - 1)
            rows = [row for row in rows if datetime.date.fromisoformat(row["date"]) >= cutoff]
        rows.sort(key=lambda row: (row["date"], row["sku"], row["merchant"]))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(rows, open(path, "w", encoding="utf-8"), indent=1)
        print(f"price history: {len(rows)} rows through {day}", file=sys.stderr)
        return len(rows)
    except Exception as exc:
        print(f"price history skipped: {exc}", file=sys.stderr)
        return 0


def _self_check():
    import tempfile
    deals = [
        {"id": "keep", "sku": "FS1", "retailer": "FragranceShop", "price": 10.0,
         "comps": [{"retailer": "Perfumania", "price": 11.5}, {"retailer": "Ulta", "price": 20}]},
        {"id": "other", "retailer": "FragranceNet", "price": 8.0},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "price-history.json")
        n1 = record(deals, "2026-11-27T15:24:37Z", path)
        n2 = record(deals, "2026-11-27T18:00:00Z", path)
        rows = load(path)
        if n1 != n2 or n1 != len(rows) or len(rows) != 3:
            raise SystemExit(f"same-day rerun was not idempotent ({n1}, {n2}, {len(rows)})")
        if any(row["merchant"] == "Ulta" for row in rows):
            raise SystemExit("Ulta was stored")
        dropped = [deals[1]]
        n3 = record(dropped, "2026-11-27T19:00:00Z", path)
        rows = load(path)
        if n3 != 3 or not any(row["sku"] == "FS1" for row in rows):
            raise SystemExit("a dropped SKU removed history or failed the write")
        open(path, "w", encoding="utf-8").write("{not json")
        n4 = record(dropped, "2026-11-28T15:00:00Z", path)
        rows = load(path)
        if n4 != 1 or rows[0]["date"] != "2026-11-28":
            raise SystemExit(f"a malformed file did not start fresh ({n4}, {rows})")
        old = datetime.date(2024, 1, 1).isoformat()
        json.dump([
            {"sku": "OLD", "merchant": "FragranceShop", "price": 1, "date": old},
            {"sku": "NEW", "merchant": "FragranceShop", "price": 2, "date": "2026-11-27"},
        ], open(path, "w", encoding="utf-8"))
        record([{"sku": "NEW", "retailer": "FragranceShop", "price": 3}], "2026-11-27T15:00:00Z", path)
        rows = load(path)
        if any(row["sku"] == "OLD" for row in rows):
            raise SystemExit("a row older than 400 days was kept")
        if not any(row["sku"] == "NEW" and row["price"] == 3 for row in rows):
            raise SystemExit("today's price was not replaced")
        os.remove(path)
        if load(path):
            raise SystemExit("a missing file did not read as empty")
    print("price history ok")


if __name__ == "__main__":
    _self_check()
