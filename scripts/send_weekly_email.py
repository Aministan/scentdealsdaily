#!/usr/bin/env python3
"""Send the Friday ScentDealsDaily newsletter through Brevo, or write a dry-run preview.

Reads data/deals.json (the same file scripts/build.py renders). Prices, names, and
stores come only from that file. Deal links point at scentdealsdaily.com pages.
"""
import argparse, html, json, os, re, sys, urllib.error, urllib.request
import links
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEALS_PATH = ROOT / "data" / "deals.json"
PREVIEW_PATH = ROOT / "out" / "weekly-email-preview.html"
ARTIFACT_PATH = Path("/opt/cursor/artifacts/weekly-email-preview.html")
SITE = "https://scentdealsdaily.com"
LIST_ID = 3
SUBJECT = "This week's best fragrance deals"
PREVIEW = "Authentic bottles, real price drops, checked this week."
INTRO = "This week's best fragrance price drops, all from authorized retailers."
API = "https://api.brevo.com/v3"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
ACCENT = "#6b2d5c"

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def fullname(d):
    brand, name = d["brand"], d["name"]
    if name.lower().startswith(brand.lower() + " "):
        return name
    return f"{brand} {name}"

def deal_page(d):
    path = slug(d["brand"] + " " + d["name"])
    if d.get("url_size"):
        path = slug(f"{d['brand']} {d['name']} {d.get('size') or ''}")
    return f"{SITE}/fragrance/{path}/?utm_source=newsletter&utm_medium=email&utm_campaign=weekly"

def money(n):
    return f"${n:,.2f}"

def was_price(d):
    """Compare-at price from the data, only when it is a real higher number."""
    was, price = d.get("was"), d.get("price")
    if isinstance(was, bool) or isinstance(price, bool):
        return None
    if isinstance(was, (int, float)) and isinstance(price, (int, float)) and was > price:
        return was
    return None

def pick_deals(data, limit=8):
    chosen = []
    for d in data.get("deals") or []:
        price = d.get("price")
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            continue
        if d.get("in_stock") is False:
            continue
        chosen.append(d)
    def rank(d):
        pct = d.get("pct_off")
        if isinstance(pct, bool) or not isinstance(pct, (int, float)):
            pct = -1
        return (pct, d.get("checked") or "")
    chosen.sort(key=rank, reverse=True)
    return chosen[:limit]

def campaign_name(now=None):
    day = (now or datetime.now(ZoneInfo("America/New_York"))).date().isoformat()
    return f"ScentDealsDaily Friday deals {day}"

def render_email(deals):
    rows = []
    for d in deals:
        name = html.escape(fullname(d), quote=False)
        size = re.sub(r"\s+", " ", d.get("size") or "").strip()
        store = html.escape(d.get("retailer") or "", quote=False)
        bits = []
        if size:
            bits.append(html.escape(size, quote=False))
        price = money(d["price"])
        was = was_price(d)
        if was is not None:
            price += f' <span style="color:#5c5c5c;text-decoration:line-through;">{money(was)}</span>'
        bits.append(price)
        if store:
            bits.append(store)
        href = html.escape(deal_page(d), quote=True)
        rows.append(f"""<tr><td style="padding:16px 0;border-top:1px solid #eeeeee;font-family:{FONT};color:#222222;">
<p style="margin:0 0 6px;font-size:17px;line-height:1.35;font-weight:600;color:#222222;">{name}</p>
<p style="margin:0 0 10px;font-size:15px;line-height:1.45;color:#222222;">{" · ".join(bits)}</p>
<a href="{href}" style="color:{ACCENT};font-size:15px;text-decoration:underline;">See the deal</a>
</td></tr>""")
    body = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(SUBJECT, quote=False)}</title>
</head>
<body style="margin:0;padding:0;background:#ffffff;color:#222222;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;color:#ffffff;">{html.escape(PREVIEW, quote=False)}&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
<tr><td align="center" style="padding:0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
<tr><td style="padding:28px 20px 8px;font-family:{FONT};font-size:22px;line-height:1.3;font-weight:700;color:#222222;">ScentDealsDaily</td></tr>
<tr><td style="padding:0 20px 8px;font-family:{FONT};font-size:16px;line-height:1.5;color:#222222;">{html.escape(INTRO, quote=False)}</td></tr>
<tr><td style="padding:8px 20px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
{body}
</table>
</td></tr>
<tr><td style="padding:20px 20px 32px;border-top:1px solid #eeeeee;font-family:{FONT};font-size:13px;line-height:1.5;color:#444444;">
<p style="margin:0 0 8px;">You're getting this because you subscribed at scentdealsdaily.com.</p>
<p style="margin:0 0 8px;">We may earn a commission when you buy through our links.</p>
<p style="margin:0;"><a href="__UNSUBSCRIBE__" style="color:{ACCENT};text-decoration:underline;">Unsubscribe</a></p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
""".replace("__UNSUBSCRIBE__", "{{ unsubscribe }}")

def write_preview(doc):
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_PATH.write_text(doc)
    print(f"Wrote {PREVIEW_PATH}")
    try:
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_PATH.write_text(doc)
        print(f"Wrote {ARTIFACT_PATH}")
    except OSError as err:
        print(f"Could not write {ARTIFACT_PATH}: {err}")

def dry_run_requested(args):
    if args.dry_run:
        return True
    return os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes", "y"}

def brevo(method, path, key, body=None):
    data = None if body is None else json.dumps(body).encode()
    target = links.safe_request_url(API + path)
    if not target:
        print("refusing to request an affiliate tracking url", file=sys.stderr)
        raise SystemExit(1)
    req = urllib.request.Request(
        target,
        data=data,
        method=method,
        headers={"api-key": key, "accept": "application/json", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")
        print(f"Brevo {method} {path} failed: {err.code} {detail}", file=sys.stderr)
        raise SystemExit(1)

def send(key, doc, name):
    info = brevo("GET", f"/contacts/lists/{LIST_ID}", key)
    total = info.get("totalSubscribers") or 0
    if total == 0:
        print(f"Brevo list {LIST_ID} has no subscribers; not creating a campaign.")
        return 0
    listing = brevo("GET", "/emailCampaigns?limit=50", key)
    names = [c.get("name") for c in listing.get("campaigns") or []]
    if name in names:
        print(f"Campaign {name!r} already exists; not sending again.")
        return 0
    created = brevo("POST", "/emailCampaigns", key, {
        "name": name,
        "sender": {"name": "ScentDealsDaily", "email": "deals@scentdealsdaily.com"},
        "replyTo": "amin.peracha98@gmail.com",
        "recipients": {"listIds": [LIST_ID]},
        "subject": SUBJECT,
        "previewText": PREVIEW,
        "htmlContent": doc,
    })
    cid = created.get("id")
    if not cid:
        print(f"Brevo did not return a campaign id: {created}", file=sys.stderr)
        return 1
    brevo("POST", f"/emailCampaigns/{cid}/sendNow", key)
    print(f"Sent campaign {cid} ({name}) to list {LIST_ID}.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Send or preview the Friday fragrance deals email.")
    parser.add_argument("--dry-run", action="store_true", help="Write the HTML preview and do not call Brevo.")
    args = parser.parse_args()
    data = json.loads(DEALS_PATH.read_text())
    deals = pick_deals(data)
    if not deals:
        print("No current deals in data/deals.json; not sending.")
        return 0
    doc = render_email(deals)
    name = campaign_name()
    print(f"{len(deals)} deals for {name!r}")
    for d in deals:
        was = was_price(d)
        extra = f" was {money(was)}" if was is not None else ""
        print(f"- {fullname(d)} {d.get('size') or ''} {money(d['price'])}{extra} at {d.get('retailer')} ({d.get('pct_off')}% off)")
    if dry_run_requested(args):
        write_preview(doc)
        print("Dry run: did not call Brevo.")
        return 0
    key = os.environ.get("BREVO_API_KEY", "").strip()
    if not key:
        print("BREVO_API_KEY is not set; skipping weekly email.")
        return 0
    write_preview(doc)
    return send(key, doc, name)

if __name__ == "__main__":
    raise SystemExit(main())
