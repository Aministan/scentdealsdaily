#!/usr/bin/env python3
"""Render data/deals.json -> static site in site/. Usage: SITE_URL=https://... python3 scripts/build.py"""
import json, os, html, re, datetime, urllib.parse, shutil, tempfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=f"{ROOT}/site"
# site/ is wiped and regenerated; keep promo videos in site/media across that rebuild.
_media_tmp=None
if os.path.isdir(f"{OUT}/media"):
    _media_tmp=tempfile.mkdtemp(prefix="sdd-media-")
    shutil.copytree(f"{OUT}/media", f"{_media_tmp}/media")
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT, exist_ok=True)
BASE=os.environ.get("SITE_URL","https://aministan.github.io").rstrip("/")
PREFIX=os.environ.get("PATH_PREFIX","/scentdealsdaily")  # e.g. /scentdealsdaily for GitHub project pages
NEWSLETTER_ENDPOINT=os.environ.get("NEWSLETTER_ENDPOINT","#newsletter-placeholder")
NAME="ScentDealsDaily"
D=json.load(open(f"{ROOT}/data/deals.json"))
CFG=json.load(open(f"{ROOT}/data/config.json"))
e=html.escape
CJ_PM="https://www.tkqlhce.com/click-101905413-15733833"
CJ_FS="https://www.anrdoezrs.net/click-101905413-16941523"
def _host(url):
    return (urllib.parse.urlparse(url).hostname or "").lower()
def is_perfumania(url):
    if not isinstance(url,str) or not url: return False
    if "tkqlhce.com/click-101905413-15733833" in url: return True
    h=_host(url)
    return h=="perfumania.com" or h.endswith(".perfumania.com")
def is_fragranceshop(url):
    if not isinstance(url,str) or not url: return False
    if "anrdoezrs.net/click-101905413-16941523" in url: return True
    h=_host(url)
    return h=="fragranceshop.com" or h.endswith(".fragranceshop.com")
def is_affiliate(url):
    return is_perfumania(url) or is_fragranceshop(url)
def affiliate_url(url):
    """CJ deep link for Perfumania and FragranceShop. Other retailers stay as-is."""
    if not isinstance(url,str) or not url: return url
    if "tkqlhce.com/click-101905413-15733833" in url or "anrdoezrs.net/click-101905413-16941523" in url: return url
    cj = CJ_PM if is_perfumania(url) else CJ_FS if is_fragranceshop(url) else None
    if not cj: return url
    p=urllib.parse.urlparse(url)
    if (p.path or "") in ("","/") and not p.query and not p.fragment: return cj
    return cj+"?url="+urllib.parse.quote(url,safe="")
def ext_a(url, inner, cls="", style=""):
    href=e(affiliate_url(url))
    extra=(f' class="{cls}"' if cls else "")+(f" style='{style}'" if style else "")
    if is_affiliate(url):
        return f'<a{extra} rel="sponsored nofollow noopener" target="_blank" href="{href}">{inner}</a>'
    return f"<a{extra} rel='nofollow sponsored noopener' target=_blank href='{href}'>{inner}</a>"
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
import unicodedata
BRAND_CANON={"Lancome":"Lancôme"}  # Perfumania uses both spellings; one brand page
def canon(b): return BRAND_CANON.get(b,b)
def bslug(b): return slug(unicodedata.normalize("NFKD",canon(b)).encode("ascii","ignore").decode())
def sz(size): return re.sub(r"\s+"," ",size or "").strip().rstrip(".")
def fullname(d):
    """Display name without a doubled brand ("Azzaro Azzaro Cologne" -> "Azzaro Cologne"). URLs keep brand+name slugs."""
    b,n=d['brand'],d['name']
    return n if n.lower().startswith(b.lower()+" ") else f"{b} {n}"
def oz(size):
    m=re.match(r"\s*([0-9]*\.?[0-9]+)\s*oz",size or "",re.I); return float(m.group(1)) if m else None
def per_oz(d):
    o=oz(d.get('size')); return d['price']/o if o else None
def money(x): return f"${x:,.2f}"
upd=datetime.datetime.strptime(D["updated"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
upd_h=upd.astimezone(datetime.timezone(datetime.timedelta(hours=-4))).strftime("%b %-d, %Y %-I:%M %p ET")
CSS="""*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d1b20;background:#faf8f5}
a{color:#6b2d5c}header{background:#1d1b20;color:#fff;padding:14px 16px}header a{color:#fff;text-decoration:none}
.logo{font-weight:800;font-size:20px;letter-spacing:-.5px}.logo span{color:#e7b75f}nav{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;font-size:14px}
main{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:26px;line-height:1.2;margin:8px 0}.sub{color:#5f5a66;margin:0 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.card{background:#fff;border:1px solid #ece7e1;border-radius:14px;padding:12px;display:flex;flex-direction:column}
.card img{width:100%;aspect-ratio:1;object-fit:contain;background:#fff}.badge{display:inline-block;background:#c0392b;color:#fff;border-radius:6px;padding:1px 7px;font-size:13px;font-weight:700}
.brand{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#7a7480;margin-top:6px}.nm{font-weight:650;margin:2px 0}
.price{font-size:22px;font-weight:800}.was{color:#8d8791;text-decoration:line-through;margin-left:6px}.meta{font-size:12px;color:#7a7480}.also{font-size:12px;color:#7a7480;margin:6px 0 8px}
.btn{display:block;text-align:center;background:#6b2d5c;color:#fff;border-radius:10px;padding:10px;margin-top:auto;text-decoration:none;font-weight:650}
.box{background:#fff;border:1px solid #ece7e1;border-radius:14px;padding:16px;margin:18px 0}
form{display:flex;gap:8px;flex-wrap:wrap}input[type=email]{flex:1;min-width:200px;padding:11px;border:1px solid #ccc;border-radius:10px;font-size:16px}
button{background:#e7b75f;border:0;border-radius:10px;padding:11px 16px;font-weight:700;font-size:16px}
table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;padding:10px;border-bottom:1px solid #eee;vertical-align:top}
.chips a{display:inline-block;margin:3px;padding:4px 10px;border-radius:99px;background:#fff;border:1px solid #e3ddd6;text-decoration:none;font-size:14px}
footer{max-width:1100px;margin:20px auto;padding:16px;font-size:13px;color:#6f6976}
@media(max-width:640px){table,thead,tbody,tr,td{display:block}thead{display:none}td{border:0;padding:4px 10px}tr{border-bottom:1px solid #eee;padding:8px 0}}"""
def page(path,title,desc,body,jsonld=None):
    url=f"{BASE}{PREFIX}/{path}".replace("/index.html","/")
    ld="".join(f'<script type="application/ld+json">{json.dumps(j,ensure_ascii=False)}</script>' for j in (jsonld or []))
    p=PREFIX
    doc=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="GASeKy1uEWpsrSn1II701znBYlw6mBhAwvimW0Yi8Io" />
<meta name='impact-site-verification' value='6f939439-73de-427f-89fc-c18dc2f9f64d'>
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">
<meta name="twitter:card" content="summary"><link rel="stylesheet" href="{p}/style.css">{ld}</head><body>
<header><a class="logo" href="{p}/">Scent<span>Deals</span>Daily</a><nav><a href="{p}/">Today's deals</a><a href="{p}/dupes/">Dupes</a><a href="{p}/men/">Men</a><a href="{p}/women/">Women</a><a href="{p}/brands/">Brands</a><a href="{p}/sponsor/">Sponsor</a></nav></header>
<main>{body}</main><footer><p>We may earn a commission when you buy through our links, at no extra cost to you. Affiliate links go to Perfumania and FragranceShop.</p>
<p><b>Affiliate disclosure:</b> some links may earn us a commission at no cost to you. <a href="{p}/disclosure/">Details</a>.
We list only authorized or long-established retailers, never gray-market marketplaces. Prices change fast; each deal shows when we last checked it. Not affiliated with any brand.</p>
<p>© {upd.year} {NAME} · <a href="{p}/llms.txt">llms.txt</a> · <a href="{p}/sitemap.xml">sitemap</a></p>
<p><img src="https://hits.sh/aministan.github.io/scentdealsdaily.svg?label=visitors" alt="visitor count" loading="lazy" height="20"></p></footer></body></html>"""
    fp=f"{OUT}/{path}"; os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w").write(doc); PAGES.append(url)
PAGES=[]
def also_line(d):
    a=d.get("also")
    if not a or a.get("price") is None or not a.get("url"): return ""
    return f"<div class='also'>also at {ext_a(a['url'], e(a['retailer']))} · ${a['price']:.2f}</div>"
def card(d,eager=False):
    ld='fetchpriority="high"' if eager else 'loading="lazy"'
    return f"""<article class="card"><img {ld} decoding="async" src="{e(d['image'] or '')}" alt="{e(fullname(d))}" width="400" height="400">
<div><span class="badge">-{d['pct_off']}%</span></div><div class="brand">{e(canon(d['brand']))}</div><div class="nm"><a href="{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/">{e(d['name'])}</a> · {e(d['size'])}</div>
<div><span class="price">${d['price']:.2f}</span><span class="was">${d['was']:.2f}</span></div>
<div class="meta">at {e(d['retailer'])} · checked {upd_h} · {('crossed-out = price at '+e(d['was_label'])) if d.get('was_label') else '"was" = retailer\'s listed compare-at price'}</div>
{also_line(d)}
{ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn")}</article>"""
def itemlist(ds,name):
    return {"@context":"https://schema.org","@type":"ItemList","name":name,"itemListElement":[{"@type":"ListItem","position":i+1,"item":{
      "@type":"Product","name":f"{fullname(d)} {d['size']}","brand":{"@type":"Brand","name":canon(d['brand'])},"image":d['image'],
      "offers":{"@type":"Offer","price":f"{d['price']:.2f}","priceCurrency":"USD","availability":"https://schema.org/InStock","url":affiliate_url(d['url']),
      "seller":{"@type":"Organization","name":d['retailer']},"priceValidUntil":(upd+datetime.timedelta(days=1)).strftime('%Y-%m-%d')}}} for i,d in enumerate(ds)]}
signup=f"""<section class="box" id="newsletter"><h2 style="margin-top:0">Get the 5 best fragrance deals every morning</h2>
<p class="sub">Free daily email. Only authentic bottles from real retailers. Unsubscribe anytime.</p>
<form action="{e(NEWSLETTER_ENDPOINT)}" method="post" onsubmit="if(this.action.endsWith('#newsletter-placeholder')){{event.preventDefault();this.innerHTML='<b>Thanks! Signups open very soon.</b>'}}">
<input type="email" name="email" required placeholder="you@email.com" aria-label="Email"><button>Subscribe</button></form></section>"""
deals=D["deals"]
# ---- roundups (/best/...) and dupe hubs (/dupes/<hub>/): data-driven so they survive the daily rebuild ----
U50="the price must be under $50 right now"
ROUNDUPS=[r for r in [
  {"slug":"cologne-deals-under-50","title":"Best Cologne Deals Under $50","noun":"cologne","who":"men's and unisex","scope":"under $50","rule":U50,"items":[d for d in deals if d['gender'] in ('men','unisex') and d['price']<50]},
  {"slug":"perfume-deals-under-50","title":"Best Perfume Deals Under $50","noun":"perfume","who":"women's and unisex","scope":"under $50","rule":U50,"items":[d for d in deals if d['gender'] in ('women','unisex') and d['price']<50]},
  {"slug":"fragrance-deals-under-30","title":"Best Fragrance Deals Under $30","noun":"fragrance","who":"men's, women's and unisex","scope":"under $30","rule":"the price must be under $30 right now",
   "lead":"Full-size designer bottles you can buy for less than $30 today, mixed across men's, women's and unisex picks.","items":[d for d in deals if d['price']<30]},
  {"slug":"luxury-fragrance-deals","title":"Best Luxury Fragrance Deals","noun":"luxury fragrance","who":"prestige","scope":"with a $120+ list price","rule":"the bottle's listed price (or another authorized retailer's price) must be $120 or more",
   "lead":"Prestige perfumes and colognes that normally list for $120 or more, discounted at authorized retailers today. Good for gifts or a bottle you would not usually pay full price for.","items":[d for d in deals if d['was']>=120]},
 ] if len(r["items"])>=3]
HUBS=[]
for h in CFG.get("hubs",[]):
    ms=[x for x in D["dupes"] if any(m in x["original"] for m in h["match"])]
    if len(ms)>=2: HUBS.append(dict(h,items=ms,topic=h["title"].replace("Best ","").replace(" Dupes","")))
def hub_of(d): return next((h for h in HUBS if d in h["items"]),None)
BYID={d['id']:d for d in deals}
VS=[dict(v,A=BYID[v['a']],B=BYID[v['b']]) for v in CFG.get("vs",[]) if v['a'] in BYID and v['b'] in BYID]
def vs_of(d): return [v for v in VS if d is v['A'] or d is v['B']]
def bestchips(): return ("<section class='box'><h2 style='margin-top:0'>Shop by budget &amp; dupe guides</h2><div class='chips'>"
    +"".join(f"<a href='{PREFIX}/best/{r['slug']}/'>{e(r['title'])}</a>" for r in ROUNDUPS)
    +"".join(f"<a href='{PREFIX}/dupes/{h['slug']}/'>{e(h['title'])}</a>" for h in HUBS)
    +"".join(f"<a href='{PREFIX}/vs/{v['slug']}/'>{e(v['title'])}</a>" for v in VS)+"</div></section>") if (ROUNDUPS or HUBS or VS) else ""
page("index.html",f"Today's Best Designer Fragrance Deals ({upd:%b %-d}) | {NAME}",
 f"{len(deals)} hand-checked discounts on authentic designer perfume & cologne from reputable retailers, updated daily. Plus the best dupes.",
 f"<h1>Today's best designer fragrance deals</h1><p class='sub'>{len(deals)} live deals on authentic bottles · last checked {upd_h} · sorted by % off</p>"
 +f"<div class='grid'>{''.join(card(d,i<2) for i,d in enumerate(deals))}</div>{bestchips()}{signup}"
 +"<section class='box'><h2 style='margin-top:0'>Why trust these deals?</h2><p>We only list authorized or long-established retailers (no anonymous marketplace sellers), re-check every price and stock status daily, and drop expired deals automatically. Want the smell for less? See our <a href='"+PREFIX+"/dupes/'>dupes directory</a>.</p></section>",
 [itemlist(deals,"Today's designer fragrance deals"),{"@context":"https://schema.org","@type":"WebSite","name":NAME,"url":BASE+PREFIX+"/"}])
# dupes
rows="".join(f"""<tr><td><b>{e(d['original'])}</b>{('<div class=meta>'+e(d['original_price'])+'</div>') if d.get('original_price') else ''}</td>
<td><b><a href='{PREFIX}/dupe/{slug(d["original"]+" dupe "+d["dupe"])}/'>{e(d['dupe'])}</a></b><div class=meta>{e(d['notes'])}</div></td>
<td>{(f"<b>${d['price']:.2f}</b> ({e(d['size'])}) {ext_a(d['url'], e(d.get('retailer') or 'Retailer'))}<div class=meta>checked {upd_h}</div>") if d['price'] else "<span class=meta>Not tracked yet — price check coming</span>"}</td>
<td class=meta>{' '.join((f'<a href="{e(affiliate_url(s))}" rel="sponsored nofollow noopener" target="_blank">[{i+1}]</a>' if is_perfumania(s) else f"<a href='{e(s)}' rel=noopener target=_blank>[{i+1}]</a>") for i,s in enumerate(d['sources']))}</td></tr>""" for d in D["dupes"])
faq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the best dupe for {d['original']}?","acceptedAnswer":{"@type":"Answer","text":f"{d['dupe']} is a widely cited alternative to {d['original']} ({d['notes']})."+(f" It was ${d['price']:.2f} for {d['size']} at {d.get('retailer') or 'the retailer'} as of {upd:%Y-%m-%d}." if d['price'] else "")}} for d in D["dupes"]]}
page("dupes/index.html",f"Best Designer Fragrance Dupes {upd.year}: {len(D['dupes'])} Clones With Live Prices | {NAME}",
 "Creed Aventus, Baccarat Rouge 540, Angels' Share, Sauvage Elixir and more: the most-cited affordable dupes, with today's prices and sources.",
 f"<h1>Designer fragrance dupes directory</h1><p class='sub'>Popular designer → affordable alternative pairs, cited from fragrance community rankings. Dupes are legally sold originals \"inspired by\" a scent — not counterfeits.</p>"+(("<p class='chips'>Compare guides: "+"".join(f"<a href='{PREFIX}/dupes/{h['slug']}/'>{e(h['title'])}</a>" for h in HUBS)+"</p>") if HUBS else "")+f"<table><thead><tr><th>Designer original</th><th>Dupe</th><th>Today's price</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>{signup}",[faq])
# gender/category pages
for g,label in [("men","Men's Cologne"),("women","Women's Perfume"),("unisex","Unisex Fragrance")]:
    ds=[d for d in deals if d["gender"]==g]
    if not ds: continue
    tb=", ".join(dict.fromkeys(d['brand'] for d in ds))
    tb=tb if len(tb)<50 else tb[:tb.rfind(",",0,50)]+" & more"
    page(f"{g}/index.html",f"{label} Deals Today ({upd:%b %-d}): Up to {max(d['pct_off'] for d in ds)}% Off | {NAME}",
      f"{len(ds)} authentic {label.lower()} deals from ${min(d['price'] for d in ds):.2f}, up to {max(d['pct_off'] for d in ds)}% off at authorized retailers: {tb}. Checked {upd:%b %-d}.",
      f"<h1>{label} deals</h1><p class='sub'>{len(ds)} live · checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{bestchips()}{signup}",[itemlist(ds,label+" deals")])
brands=sorted({canon(d["brand"]) for d in deals})
for b in brands:
    ds=[d for d in deals if canon(d["brand"])==b]
    nm=", ".join(fullname(d).replace(b+" ","",1) for d in ds[:2])+(" & more" if len(ds)>2 else "")
    page(f"brands/{bslug(b)}/index.html",f"{b} Perfume & Cologne Deals: Up to {max(d['pct_off'] for d in ds)}% Off Today | {NAME}",
      f"{len(ds)} verified {b} fragrance deal{'s' if len(ds)>1 else ''} from ${min(d['price'] for d in ds):.2f} ({nm}). Authentic, price-checked {upd:%b %-d, %Y}.",
      f"<h1>{e(b)} deals</h1><p class='sub'>checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{signup}",[itemlist(ds,b+" deals")])
page("brands/index.html",f"Fragrance Deals by Brand: {len(brands)} Designer Brands on Sale Today | {NAME}",f"Browse today's verified perfume and cologne discounts from {len(brands)} brands including {', '.join(brands[:4])}. Authorized retailers only, checked daily.",
 "<h1>Deals by brand</h1><div class='chips'>"+"".join(f"<a href='{PREFIX}/brands/{bslug(b)}/'>{e(b)}</a>" for b in brands)+"</div>")
page("sponsor/index.html",f"Sponsor {NAME} / Feature Your Brand","Reach fragrance shoppers actively looking to buy. Featured listings and newsletter sponsorships.",
 f"""<h1>Feature your fragrance brand</h1><p class='sub'>Put your scent in front of shoppers who are ready to buy.</p>
<div class='box'><h2 style='margin-top:0'>Options</h2><ul><li><b>Featured deal</b> — pinned at the top of the homepage for 7 days, clearly labeled "Sponsored".</li>
<li><b>Newsletter sponsor</b> — one slot in the daily email.</li><li><b>Dupe spotlight</b> — your house featured on the dupes directory (must be an original composition, not a counterfeit).</li></ul>
<p>Rules: authentic products only, every sponsored placement labeled, no fake reviews.</p>
<p>Contact: <a href="mailto:hello@scentdealsdaily.com">hello@scentdealsdaily.com</a> (pricing on request).</p></div>""")
page("disclosure/index.html",f"Affiliate Disclosure | {NAME}","How ScentDealsDaily earns money: retailer affiliate commissions at no extra cost to you and clearly labeled sponsored spots. Deals are always ranked by % off.",
 """<h1>Affiliate disclosure</h1><div class='box'><p>We may earn a commission when you buy through our links, at no extra cost to you.</p>
<p>Some links on this site are affiliate links, including links to Perfumania and FragranceShop. If you buy through them, we may earn a commission at no extra cost to you. This never changes which deals we list or how they're ranked (by % off). When the same sealed bottle is in stock at both stores, the buy button goes to the lower price we checked, and the other store is noted beside it.</p>
<p>As an Amazon Associate we may earn from qualifying purchases (once enrolled). Sponsored placements are always labeled "Sponsored".</p>
<p>"Was" prices are the retailer's own listed compare-at / retail price at the time we checked. Prices and stock change; always confirm at checkout.</p></div>""")
open(f"{OUT}/style.css","w").write(CSS)
open(f"{OUT}/robots.txt","w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}{PREFIX}/sitemap.xml\n")
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
llms=[f"# {NAME}",f"> Daily-checked discounts on authentic designer fragrances at reputable retailers, plus a cited dupes directory. Last updated {D['updated']}.","",
 "## Today's deals (price USD, size, retailer, % off listed compare-at)"]+[f"- {d['brand']} {d['name']} {d['size']}: ${d['price']:.2f} (was ${d['was']:.2f}, -{d['pct_off']}%) at {d['retailer']}: {affiliate_url(d['url'])}" for d in deals]+["","## Dupes (designer original -> alternative)"]+[f"- {d['original']} -> {d['dupe']}"+(f": ${d['price']:.2f} {d['size']} at {d['retailer']} {affiliate_url(d['url'])}" if d['price'] else "")+f" (sources: {', '.join(affiliate_url(s) if is_perfumania(s) else s for s in d['sources'])})" for d in D['dupes']]+["","## Pages",f"- Deals: {BASE}{PREFIX}/",f"- Dupes: {BASE}{PREFIX}/dupes/",f"- Raw data (JSON): {BASE}{PREFIX}/deals.json"]
open(f"{OUT}/llms.txt","w").write("\n".join(llms)+"\n")
json.dump(D,open(f"{OUT}/deals.json","w"))
open(f"{OUT}/.nojekyll","w").write("")
print(len(PAGES),"pages ->",OUT)

def comprows(d):
    cs=d.get('comps') or [{"retailer":d['retailer'],"price":d['price'],"url":d['url'],"checked":upd_h}]
    cs=sorted(cs,key=lambda c:c['price'])
    return "".join(f"<tr><td>{ext_a(c['url'], e(c['retailer']))}{' <span class=badge>lowest</span>' if i==0 else ''}</td><td>{e(d.get('size') or '')}</td><td><b>${c['price']:.2f}</b></td><td class=meta>{e(c['checked'] if 'T' not in str(c['checked']) else upd_h)}</td></tr>" for i,c in enumerate(cs))
# ---------- SEO landing pages: one per fragrance deal + one per dupe pair ----------
import hashlib
def faqld(qs): return {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in qs]}
def faqhtml(qs): return "<section class='box'><h2 style='margin-top:0'>FAQ</h2>"+"".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q,a in qs)+"</section>"
def buy(url,ret): return ext_a(url, f"Buy at {e(ret)} →", cls="btn", style="max-width:340px")
def prod_ld(name,brand,img,price,url,ret,was=None):
    o={"@type":"Offer","price":f"{price:.2f}","priceCurrency":"USD","availability":"https://schema.org/InStock","url":affiliate_url(url),"seller":{"@type":"Organization","name":ret},"priceValidUntil":(upd+datetime.timedelta(days=1)).strftime('%Y-%m-%d')}
    return {"@context":"https://schema.org","@type":"Product","name":name,"brand":{"@type":"Brand","name":brand},"image":img,"offers":o}
KW=[]
for d in deals:
    full=fullname(d); s=slug(f"{d['brand']} {d['name']}"); KW+= [f"{full.lower()} cheapest price",f"{full.lower()} sale",f"{full.lower()} {d['size'].lower()} deal"]
    gl={"men":"men's cologne","women":"women's perfume","unisex":"unisex fragrance"}[d['gender']]
    others=[x for x in deals if x['gender']==d['gender'] and x['id']!=d['id']][:4]
    qs=[(f"What is the cheapest price for {full} right now?",f"As of {upd_h}, the lowest price we verified is ${d['price']:.2f} for {d['size']} at {d['retailer']}, {d['pct_off']}% below {('the $%.2f at %s' % (d['was'],d['was_label'])) if d.get('was_label') else ('its listed $%.2f' % d['was'])}."),
        (f"Is {full} on sale?",f"{d['retailer']} has it at ${d['price']:.2f} versus ${d['was']:.2f} {('at '+d['was_label']) if d.get('was_label') else 'listed compare-at'}. We re-check daily and remove it when the deal ends."),
        (f"Is the {d['retailer']} {full} authentic?",f"{d['retailer']} is a long-established US fragrance chain selling genuine designer brands. We exclude marketplace sellers and tester listings."),
        (f"How much does {full} cost per ounce?",(f"At ${d['price']:.2f} for {d['size']} it works out to ${per_oz(d):.2f} per ounce, and you save ${d['was']-d['price']:.2f} versus the ${d['was']:.2f} listed price." if per_oz(d) else f"At ${d['price']:.2f} you save ${d['was']-d['price']:.2f} versus the ${d['was']:.2f} listed price."))]
    ru=next((r for r in ROUNDUPS if d in r['items']),None)
    body=(f"<h1>{e(full)} {e(sz(d['size']))}: cheapest price today</h1><p class='sub'>Lowest verified price: <b class='price'>${d['price']:.2f}</b> <span class='was'>${d['was']:.2f}</span> <span class='badge'>-{d['pct_off']}%</span> at {e(d['retailer'])} · checked {upd_h}</p>"
      +buy(d['url'],d['retailer'])+also_line(d)
      +f"<div class='box' style='display:flex;gap:16px;flex-wrap:wrap'><img src='{e(d['image'] or '')}' alt='{e(full)}' width=220 height=220 style='object-fit:contain'><div style='flex:1;min-width:220px'><h2 style='margin-top:0'>Price comparison</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table><p class=meta>More retailers are added as we verify them. We never list unverified prices.</p></div></div>"
      +f"<p>{e(full)} is one of today's best {gl} deals: {d['pct_off']}% {('below the '+e(d['was_label'])+' price') if d.get('was_label') else 'off the listed price'}, a {d['type'].lower() or 'fragrance'} from {e(d['brand'])} (<a href='{PREFIX}/brands/{bslug(d['brand'])}/'>all {e(canon(d['brand']))} deals</a>{(", <a href='"+PREFIX+"/best/"+ru['slug']+"/'>"+e(ru['title'].lower().replace('best ','more '))+"</a>") if ru else ''}).</p>"
      +"".join(f"<p><b>Comparing?</b> <a href='{PREFIX}/vs/{v['slug']}/'>{e(v['title'])}: prices, size and notes side by side</a></p>" for v in vs_of(d))
      +faqhtml(qs)+"<h2>Similar deals today</h2><div class='grid'>"+"".join(card(x) for x in others)+"</div>"+signup)
    page(f"fragrance/{s}/index.html",f"{full} {sz(d['size'])} Sale: ${d['price']:.2f} ({d['pct_off']}% Off) – Cheapest Price {upd:%b %Y}",
      f"{full} {sz(d['size'])} for ${d['price']:.2f} at {d['retailer']} ("+(f"${d['was']:.2f} at {d['was_label']}" if d.get('was_label') else f"was ${d['was']:.2f}")+f"). Authentic, sealed, price-checked {upd:%b %-d, %Y}.",body,
      [prod_ld(f"{full} {d['size']}",d['brand'],d['image'],d['price'],d['url'],d['retailer']),faqld(qs)])
for d in D["dupes"]:
    s=slug(f"{d['original']} dupe {d['dupe']}"); o=d['original']
    KW+=[f"{o.lower()} dupe",f"best cheap {o.lower()} dupe {upd.year}",f"{d['dupe'].lower()} vs {o.lower()}"]
    pr=f"${d['price']:.2f} for {d['size']} at {d['retailer']}" if d['price'] else "not yet price-verified by us"
    qs=[(f"What is the best cheap {o} dupe in {upd.year}?",f"{d['dupe']} is one of the most-cited affordable alternatives to {o}: {d['notes']}. Today: {pr}."),
        (f"Does {d['dupe']} smell like {o}?",f"Community rankings rate it as close ({d['notes']}). It is an original 'inspired by' fragrance, not a counterfeit; expect differences in the dry-down."),
        (f"Where can I buy {d['dupe']} cheapest?",f"The lowest price we verified is {pr}" + (f" (checked {upd_h})." if d['price'] else ". Check back; we add prices only after verifying them."))]
    rel=[x for x in D['dupes'] if x is not d][:5]
    hb=hub_of(d); hublink=(f"<a href='{PREFIX}/dupes/{hb['slug']}/'>Compare every {e(hb['topic'])} dupe side by side</a> · ") if hb else ""
    body=(f"<h1>Best {e(o)} dupe: {e(d['dupe'])}</h1><p class='sub'>{e(d['notes'])} · {('<b class=price>$%.2f</b> today at %s' % (d['price'],e(d['retailer']))) if d['price'] else 'price not verified yet'}</p>"
      +((buy(d['url'],d['retailer'])+also_line(d)) if d['price'] else "")
      +f"<div class='box'><h2 style='margin-top:0'>{e(o)} vs {e(d['dupe'])}</h2><table><thead><tr><th></th><th>{e(o)}</th><th>{e(d['dupe'])}</th></tr></thead><tbody><tr><td>Price</td><td>{e(d.get('original_price') or 'varies')}</td><td>{('$%.2f (%s)' % (d['price'],e(d['size']))) if d['price'] else '—'}</td></tr><tr><td>Profile</td><td colspan=2>{e(d['notes'])}</td></tr><tr><td>Sources</td><td colspan=2>{' '.join((f'<a href="{e(affiliate_url(x))}" rel="sponsored nofollow noopener" target="_blank">[{i+1}]</a>' if is_perfumania(x) else f'<a href={e(x)} rel=noopener target=_blank>[{i+1}]</a>') for i,x in enumerate(d['sources']))}</td></tr></tbody></table></div>"
      +((f"<div class='box'><h2 style='margin-top:0'>Where to buy {e(d['dupe'])} cheapest</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table></div>") if d.get('comps') else "")+faqhtml(qs)+"<h2>More dupes</h2><div class='chips'>"+"".join(f"<a href='{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/'>{e(x['original'])} → {e(x['dupe'])}</a>" for x in rel)+"</div><p>"+hublink+f"<a href='{PREFIX}/dupes/'>All dupes</a></p>"+signup)
    lds=[faqld(qs)]+([prod_ld(d['dupe'],d['dupe'].split()[0],d.get('image'),d['price'],d['url'],d['retailer'])] if d['price'] else [])
    page(f"dupe/{s}/index.html",f"Best {o} Dupe {upd.year}: {d['dupe']}"+(f" ${d['price']:.2f}" if d['price'] else ""),
      f"{d['dupe']} vs {o}: {d['notes'].split(';')[0].rstrip('.')}."+(f" ${d['price']:.2f} for {d['size']} at {d['retailer']} today." if d['price'] else "")+" Cited sources, authentic bottles only.",body,lds)
def picks(cheap,val,big):
    """Quick-pick bullets; merges labels when one bottle wins several, so the list never repeats itself."""
    out=[]
    for lab,d,extra in [("Lowest price",cheap,f"{cheap['size']} at ${cheap['price']:.2f}"),("best value per ounce",val,(f"${per_oz(val):.2f}/oz" if per_oz(val) else None)),("biggest discount",big,f"-{big['pct_off']}%")]:
        if not extra: continue
        hit=next((o for o in out if o[1] is d),None)
        if hit: hit[0].append(lab); hit[2].append(extra)
        else: out.append(([lab],d,[extra]))
    return "".join(f"<li><b>{e(' + '.join(l).capitalize())}:</b> <a href='{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/'>{e(fullname(d))}</a> ({e(', '.join(x))})</li>" for l,d,x in out)
# ---------- buying-guide roundups (/best/<slug>/) ----------
def offer_item(name,brand,img,price,url,ret):
    x=prod_ld(name,brand,img,price,url,ret); x.pop("@context",None); return x
for r in ROUNDUPS:
    ds=sorted(r["items"],key=lambda d:(per_oz(d) or 999,d['price'])); n=len(ds); N=r['noun']
    cheap=min(ds,key=lambda d:d['price']); val=ds[0]; big=max(ds,key=lambda d:d['pct_off'])
    SC=r['scope']; KW+=[r['title'].lower().replace('best ','best cheap ').replace(' deals',''),r['title'].lower(),f"designer {N} {SC}"]
    others=[x for x in ROUNDUPS if x is not r]
    rows="".join(f"<tr><td><a href='{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/'>{e(fullname(d))}</a><div class=meta>{e(d['type'] or '')}</div></td><td>{e(d['size'])}</td><td><b>${d['price']:.2f}</b> <span class=was>${d['was']:.2f}</span></td><td>{('$%.2f' % per_oz(d)) if per_oz(d) else '—'}</td><td><span class=badge>-{d['pct_off']}%</span></td><td>{ext_a(d['url'], 'Buy at '+e(d['retailer']))}</td></tr>" for d in ds)
    qs=[(f"What is the cheapest {N} deal {SC} today?",f"As of {upd_h}, the lowest verified price is {fullname(cheap)} {cheap['size']} at ${cheap['price']:.2f} from {cheap['retailer']} ({cheap['pct_off']}% off ${cheap['was']:.2f})."),
        (f"Which {N} {SC} is the best value per ounce?",f"{fullname(val)} at ${per_oz(val):.2f} per ounce (${val['price']:.2f} for {val['size']})." if per_oz(val) else f"{fullname(val)} at ${val['price']:.2f}."),
        (f"Which {N} {SC} has the biggest discount?",f"{fullname(big)}: {big['pct_off']}% off, ${big['price']:.2f} versus ${big['was']:.2f} {('at '+big['was_label']) if big.get('was_label') else 'listed compare-at'}."),
        (f"Are these {N} deals authentic?","Yes. We only list authorized, long-established retailers (Perfumania and FragranceShop, both US fragrance shops selling genuine designer brands) and exclude marketplace sellers, testers and unboxed bottles."),
        ("How often are these prices updated?",f"Every day. Each price, compare-at price and stock status is re-checked from the retailer's live product data; anything that drops below 15% off or sells out is removed automatically. Last check: {upd_h}.")]
    body=(f"<h1>{e(r['title'])} ({upd:%b %-d, %Y})</h1><p class='sub'>{n} authentic {r['who']} fragrances {SC}, each at least 15% below its listed price · checked {upd_h}</p>"+(f"<p>{e(r['lead'])}</p>" if r.get('lead') else "")
      +"<div class='box'><h2 style='margin-top:0'>Quick picks</h2><ul>"+picks(cheap,val,big)+"</ul>"
      +"<p class='meta'>How we pick: "+r['rule']+", at least 15% below the retailer's listed compare-at price (or another authorized retailer's price, where shown), in stock, and sold by an authorized retailer. Sorted by price per ounce so bigger bottles get credit for real value, not just a low sticker.</p></div>"
      +f"<table><thead><tr><th>Fragrance</th><th>Size</th><th>Price</th><th>Per oz</th><th>Off</th><th></th></tr></thead><tbody>{rows}</tbody></table>"
      +f"<h2>All {n} picks</h2><div class='grid'>{''.join(card(d) for d in ds)}</div>"+faqhtml(qs)
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/best/{x['slug']}/'>{e(x['title'])}</a>" for x in others)+f"<a href='{PREFIX}/men/'>All men's deals</a><a href='{PREFIX}/women/'>All women's deals</a><a href='{PREFIX}/dupes/'>Designer dupes</a></p>"+signup)
    il={"@context":"https://schema.org","@type":"ItemList","name":r['title'],"numberOfItems":n,"itemListElement":[{"@type":"ListItem","position":i+1,"item":offer_item(f"{fullname(d)} {d['size']}",d['brand'],d['image'],d['price'],d['url'],d['retailer'])} for i,d in enumerate(ds)]}
    page(f"best/{r['slug']}/index.html",f"{r['title']} Today ({upd:%b %-d}): {n} Authentic Picks | {NAME}",
      f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off, from ${cheap['price']:.2f} ({fullname(cheap)}). Ranked by price per ounce, checked {upd:%b %-d, %Y}.",body,[il,faqld(qs)])
def house(name):
    w=name.split(); return " ".join(w[:2]) if w[0] in ("Al","Ariana") else w[0]
def srclinks(srcs): return " ".join((f'<a href="{e(affiliate_url(u))}" rel="sponsored nofollow noopener" target="_blank">[{i+1}]</a>' if is_perfumania(u) else f"<a href='{e(u)}' rel=noopener target=_blank>[{i+1}]</a>") for i,u in enumerate(srcs))
def hubrow(x):
    link=f"{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/"
    op=f"<div class=meta>{e(x['original_price'])}</div>" if x.get('original_price') else ""
    if x.get('price'):
        price=f"<b>${x['price']:.2f}</b> ({e(x['size'])}) "+ext_a(x['url'],e(x['retailer'])); po=per_oz(x); pz=f"${po:.2f}" if po else "—"
    else: price="<span class=meta>not price-verified yet</span>"; pz="—"
    return f"<tr><td><b>{e(x['original'])}</b>{op}</td><td><b><a href='{link}'>{e(x['dupe'])}</a></b><div class=meta>{e(x['notes'])}</div></td><td>{price}</td><td>{pz}</td><td class=meta>{srclinks(x['sources'])}</td></tr>"
# ---------- dupe hubs (/dupes/<slug>/) ----------
for h in HUBS:
    ms=h["items"]; T=h["topic"]; pr=[x for x in ms if x.get('price')]
    rows="".join(hubrow(x) for x in ms)
    cheapest=min(pr,key=lambda x:x['price']) if pr else None
    houses=", ".join(dict.fromkeys(house(x['dupe']) for x in ms))
    KW+=[f"best {T.lower()} dupes",f"{T.lower()} dupes {upd.year}",f"cheapest {T.lower()} dupe"]
    qs=[(f"What is the cheapest {T} dupe right now?",(f"{cheapest['dupe']} at ${cheapest['price']:.2f} for {cheapest['size']} from {cheapest['retailer']}, verified {upd_h}." if cheapest else "We haven't verified a live price for these dupes yet; we only show prices we have checked.")),
        (f"What are the most-cited {T} dupes?","; ".join(f"{x['dupe']} for {x['original']} ({x['notes'].rstrip('.')}; {len(x['sources'])} cited source{'s' if len(x['sources'])>1 else ''})" for x in ms)+"."),
        (f"Are {T} dupes counterfeits?",f"No. These are original fragrances sold under their own brand names ({houses}) that fragrance communities compare to the designer scent. Counterfeits copy a designer's name and bottle; we never list those."),
        ("Where do the prices come from?",f"Dupe prices are pulled from the retailer's live product data and re-checked daily (last check {upd_h}). Designer-original prices come from the cited source and date shown next to them.")]
    body=(f"<h1>{e(h['title'])} {upd.year}: {len(ms)} alternatives compared</h1><p class='sub'>{e(h['intro'])}</p>"
      +(f"<p><b>Cheapest verified today:</b> <a href='{PREFIX}/dupe/{slug(cheapest['original']+' dupe '+cheapest['dupe'])}/'>{e(cheapest['dupe'])}</a> at ${cheapest['price']:.2f} ({e(cheapest['size'])}) · checked {upd_h}</p>"+buy(cheapest['url'],cheapest['retailer']) if cheapest else "")
      +f"<table><thead><tr><th>Designer original</th><th>Dupe &amp; profile</th><th>Today's price</th><th>Per oz</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>"
      +"<p class='meta'>Profiles summarize the cited community clone lists; how close a dupe smells is subjective and dry-downs differ. Prices are shown only after we verify them live.</p>"
      +faqhtml(qs)+"<p class='chips'>"+"".join(f"<a href='{PREFIX}/dupes/{x['slug']}/'>{e(x['title'])}</a>" for x in HUBS if x is not h)+f"<a href='{PREFIX}/dupes/'>All dupes</a></p>"+signup)
    il={"@context":"https://schema.org","@type":"ItemList","name":h['title'],"numberOfItems":len(pr),"itemListElement":[{"@type":"ListItem","position":i+1,"item":offer_item(x['dupe'],x['dupe'].split()[0],x.get('image'),x['price'],x['url'],x['retailer'])} for i,x in enumerate(pr)]}
    page(f"dupes/{h['slug']}/index.html",f"{h['title']} {upd.year}: {len(ms)} Clones Compared"+(f" From ${cheapest['price']:.2f}" if cheapest else "")+f" | {NAME}",
      f"{', '.join(x['dupe'] for x in ms)} compared: scent profiles, cited sources and verified prices"+(f" from ${cheapest['price']:.2f}" if cheapest else "")+".",body,([il] if pr else [])+[faqld(qs)])
# ---------- head-to-head comparisons (/vs/<slug>/) ----------
def conc(t):
    t=(t or "").lower()
    return "Parfum" if t.startswith("parfum") else "Eau de Parfum" if "parfum" in t else "Eau de Toilette" if "toilette" in t else (t.title() or "—")
for v in VS:
    A,B=v['A'],v['B']; fa,fb=fullname(A),fullname(B); T=v['title']
    pa,pb=per_oz(A),per_oz(B)
    cheaper=min((A,B),key=lambda d:d['price']); value=min((A,B),key=lambda d:per_oz(d) or 999); bigger=max((A,B),key=lambda d:d['pct_off'])
    ca,cb=conc(A['type']),conc(B['type'])
    def cell(d): return f"<b>${d['price']:.2f}</b> <span class=was>${d['was']:.2f}</span> <span class=badge>-{d['pct_off']}%</span>"
    def bt(d): return ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn")
    rows=(f"<tr><td>Price today</td><td>{cell(A)}</td><td>{cell(B)}</td></tr>"
      f"<tr><td>Size</td><td>{e(sz(A['size']))}</td><td>{e(sz(B['size']))}</td></tr>"
      f"<tr><td>Price per ounce</td><td>{('$%.2f' % pa) if pa else '—'}</td><td>{('$%.2f' % pb) if pb else '—'}</td></tr>"
      f"<tr><td>Concentration</td><td>{e(ca)}</td><td>{e(cb)}</td></tr>"
      f"<tr><td>Key notes</td><td>{e(v['a_notes'])}</td><td>{e(v['b_notes'])}</td></tr>"
      f"<tr><td>Cheapest at</td><td>{e(A['retailer'])}</td><td>{e(B['retailer'])}</td></tr>"
      f"<tr><td></td><td>{bt(A)}</td><td>{bt(B)}</td></tr>")
    same_conc=ca==cb
    qs=[(f"Which is cheaper, {fa} or {fb}?",f"As of {upd_h}, {fullname(cheaper)} is the lower price at ${cheaper['price']:.2f} for {sz(cheaper['size'])} ({cheaper['retailer']})."+(f" Per ounce, {fullname(value)} is the better value at ${per_oz(value):.2f}/oz." if per_oz(value) else "")),
        (f"What is the difference between {fa} and {fb}?",v['difference']),
        (f"Is {fa} or {fb} stronger?",(f"Both are sold as {ca}, so concentration alone doesn't separate them; performance depends on the composition and your skin." if same_conc else f"{fa} is an {ca} and {fb} is an {cb}. An eau de parfum (or parfum) has a higher concentration of fragrance oils than an eau de toilette, so it usually lasts longer and projects more, though skin chemistry matters.")),
        ("Are these bottles authentic?","Yes. We only link to authorized, long-established fragrance retailers (Perfumania and FragranceShop) and exclude marketplace sellers, testers and unboxed bottles. Prices are re-checked daily.")]
    KW+=[T.lower(),f"{T.lower()} which is better",f"{fa.lower()} or {fb.lower()}"]
    body=(f"<h1>{e(T)}: price, size and notes compared</h1><p class='sub'>Both on sale today · checked {upd_h}</p><p>{e(v['intro'])}</p>"
      +f"<div class='box'><h2 style='margin-top:0'>Side by side</h2><table><thead><tr><th></th><th><a href='{PREFIX}/fragrance/{slug(A['brand']+' '+A['name'])}/'>{e(fa)}</a></th><th><a href='{PREFIX}/fragrance/{slug(B['brand']+' '+B['name'])}/'>{e(fb)}</a></th></tr></thead><tbody>{rows}</tbody></table>"
      +"<p class='meta'>Prices come from each retailer's live product data. Key notes summarize the brand's published notes; how a scent wears is personal.</p></div>"
      +f"<div class='box'><h2 style='margin-top:0'>Which should you buy?</h2><ul><li><b>Lower price today:</b> {e(fullname(cheaper))} at ${cheaper['price']:.2f}.</li>"
      +(f"<li><b>Better value per ounce:</b> {e(fullname(value))} at ${per_oz(value):.2f}/oz.</li>" if per_oz(value) else "")
      +f"<li><b>Bigger discount:</b> {e(fullname(bigger))}, {bigger['pct_off']}% off.</li><li>{e(v['pick'])}</li></ul></div>"
      +faqhtml(qs)+"<h2>Both deals</h2><div class='grid'>"+card(A)+card(B)+"</div>"
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/vs/{x['slug']}/'>{e(x['title'])}</a>" for x in VS if x is not v)+f"<a href='{PREFIX}/{A['gender']}/'>All {A['gender']}'s deals</a><a href='{PREFIX}/brands/{bslug(A['brand'])}/'>All {e(canon(A['brand']))} deals</a></p>"+signup)
    page(f"vs/{v['slug']}/index.html",f"{T}: Which to Buy? Prices From ${cheaper['price']:.2f} ({upd:%b %Y}) | {NAME}",
      f"{fa} (${A['price']:.2f}, {sz(A['size'])}) vs {fb} (${B['price']:.2f}, {sz(B['size'])}): price per ounce, concentration and key notes compared. Checked {upd:%b %-d, %Y}.",body,
      [prod_ld(f"{fa} {sz(A['size'])}",canon(A['brand']),A['image'],A['price'],A['url'],A['retailer']),prod_ld(f"{fb} {sz(B['size'])}",canon(B['brand']),B['image'],B['price'],B['url'],B['retailer']),faqld(qs)])
# rewrite sitemap with new pages + keyword list + IndexNow key
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
KEY=hashlib.md5(b"scentdealsdaily-indexnow").hexdigest(); open(f"{OUT}/{KEY}.txt","w").write(KEY)
open(f"{ROOT}/docs/keywords.txt","w").write("\n".join(KW)+"\n")
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Per-product & per-dupe pages\n"+"\n".join(u for u in PAGES if "/fragrance/" in u or "/dupe/" in u)+"\n")
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Buying guides & dupe comparisons\n"+"\n".join(u for u in PAGES if "/best/" in u or "/vs/" in u or any(f"/dupes/{h['slug']}/" in u for h in HUBS))+"\n")
print(len(PAGES),"pages total;",len(KW),"keywords")
if _media_tmp:
    shutil.copytree(f"{_media_tmp}/media", f"{OUT}/media")
    shutil.rmtree(_media_tmp)
    print("copied site/media ->", OUT)
