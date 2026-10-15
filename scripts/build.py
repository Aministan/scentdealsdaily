#!/usr/bin/env python3
"""Render data/deals.json -> static site in site/. Usage: SITE_URL=https://... python3 scripts/build.py"""
import json, os, html, re, datetime, urllib.parse, shutil
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=f"{ROOT}/site"
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT, exist_ok=True)
BASE=os.environ.get("SITE_URL","https://aministan.github.io").rstrip("/")
PREFIX=os.environ.get("PATH_PREFIX","/scentdealsdaily")  # e.g. /scentdealsdaily for GitHub project pages
NEWSLETTER_ENDPOINT=os.environ.get("NEWSLETTER_ENDPOINT","#newsletter-placeholder")
NAME="ScentDealsDaily"
D=json.load(open(f"{ROOT}/data/deals.json"))
e=html.escape
CJ="https://www.tkqlhce.com/click-101905413-15733833"
def is_perfumania(url):
    if not isinstance(url,str) or not url: return False
    if "tkqlhce.com/click-101905413-15733833" in url: return True
    host=(urllib.parse.urlparse(url).hostname or "").lower()
    return host=="perfumania.com" or host.endswith(".perfumania.com")
def affiliate_url(url):
    """CJ deep link for Perfumania. Other retailers stay as-is. Bare homepage has no url= param."""
    if not isinstance(url,str) or not url: return url
    if "tkqlhce.com/click-101905413-15733833" in url: return url
    if not is_perfumania(url): return url
    p=urllib.parse.urlparse(url)
    if (p.path or "") in ("","/") and not p.query and not p.fragment: return CJ
    return CJ+"?url="+urllib.parse.quote(url,safe="")
def ext_a(url, inner, cls="", style=""):
    href=e(affiliate_url(url))
    extra=(f' class="{cls}"' if cls else "")+(f" style='{style}'" if style else "")
    if is_perfumania(url):
        return f'<a{extra} rel="sponsored nofollow noopener" target="_blank" href="{href}">{inner}</a>'
    return f"<a{extra} rel='nofollow sponsored noopener' target=_blank href='{href}'>{inner}</a>"
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
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
.price{font-size:22px;font-weight:800}.was{color:#8d8791;text-decoration:line-through;margin-left:6px}.meta{font-size:12px;color:#7a7480}
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
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">
<meta name="twitter:card" content="summary"><link rel="stylesheet" href="{p}/style.css">{ld}</head><body>
<header><a class="logo" href="{p}/">Scent<span>Deals</span>Daily</a><nav><a href="{p}/">Today's deals</a><a href="{p}/dupes/">Dupes</a><a href="{p}/men/">Men</a><a href="{p}/women/">Women</a><a href="{p}/brands/">Brands</a><a href="{p}/sponsor/">Sponsor</a></nav></header>
<main>{body}</main><footer><p>We may earn a commission when you buy through our links, at no extra cost to you.</p>
<p><b>Affiliate disclosure:</b> some links may earn us a commission at no cost to you. <a href="{p}/disclosure/">Details</a>.
We list only authorized or long-established retailers, never gray-market marketplaces. Prices change fast; each deal shows when we last checked it. Not affiliated with any brand.</p>
<p>© {upd.year} {NAME} · <a href="{p}/llms.txt">llms.txt</a> · <a href="{p}/sitemap.xml">sitemap</a></p></footer></body></html>"""
    fp=f"{OUT}/{path}"; os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w").write(doc); PAGES.append(url)
PAGES=[]
def card(d):
    return f"""<article class="card"><img loading="lazy" src="{e(d['image'] or '')}" alt="{e(d['brand']+' '+d['name'])}" width="400" height="400">
<div><span class="badge">-{d['pct_off']}%</span></div><div class="brand">{e(d['brand'])}</div><div class="nm"><a href="{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/">{e(d['name'])}</a> · {e(d['size'])}</div>
<div><span class="price">${d['price']:.2f}</span><span class="was">${d['was']:.2f}</span></div>
<div class="meta">at {e(d['retailer'])} · checked {upd_h} · {('crossed-out = price at '+e(d['was_label'])) if d.get('was_label') else '"was" = retailer\'s listed compare-at price'}</div>
{ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn")}</article>"""
def itemlist(ds,name):
    return {"@context":"https://schema.org","@type":"ItemList","name":name,"itemListElement":[{"@type":"ListItem","position":i+1,"item":{
      "@type":"Product","name":f"{d['brand']} {d['name']} {d['size']}","brand":{"@type":"Brand","name":d['brand']},"image":d['image'],
      "offers":{"@type":"Offer","price":f"{d['price']:.2f}","priceCurrency":"USD","availability":"https://schema.org/InStock","url":affiliate_url(d['url']),
      "seller":{"@type":"Organization","name":d['retailer']},"priceValidUntil":(upd+datetime.timedelta(days=1)).strftime('%Y-%m-%d')}}} for i,d in enumerate(ds)]}
signup=f"""<section class="box" id="newsletter"><h2 style="margin-top:0">Get the 5 best fragrance deals every morning</h2>
<p class="sub">Free daily email. Only authentic bottles from real retailers. Unsubscribe anytime.</p>
<form action="{e(NEWSLETTER_ENDPOINT)}" method="post" onsubmit="if(this.action.endsWith('#newsletter-placeholder')){{event.preventDefault();this.innerHTML='<b>Thanks! Signups open very soon.</b>'}}">
<input type="email" name="email" required placeholder="you@email.com" aria-label="Email"><button>Subscribe</button></form></section>"""
deals=D["deals"]
page("index.html",f"Today's Best Designer Fragrance Deals ({upd:%b %-d}) | {NAME}",
 f"{len(deals)} hand-checked discounts on authentic designer perfume & cologne from reputable retailers, updated daily. Plus the best dupes.",
 f"<h1>Today's best designer fragrance deals</h1><p class='sub'>{len(deals)} live deals on authentic bottles · last checked {upd_h} · sorted by % off</p>"
 +f"<div class='grid'>{''.join(card(d) for d in deals)}</div>{signup}"
 +"<section class='box'><h2 style='margin-top:0'>Why trust these deals?</h2><p>We only list authorized or long-established retailers (no anonymous marketplace sellers), re-check every price and stock status daily, and drop expired deals automatically. Want the smell for less? See our <a href='"+PREFIX+"/dupes/'>dupes directory</a>.</p></section>",
 [itemlist(deals,"Today's designer fragrance deals"),{"@context":"https://schema.org","@type":"WebSite","name":NAME,"url":BASE+PREFIX+"/"}])
# dupes
rows="".join(f"""<tr><td><b>{e(d['original'])}</b>{('<div class=meta>'+e(d['original_price'])+'</div>') if d.get('original_price') else ''}</td>
<td><b><a href='{PREFIX}/dupe/{slug(d["original"]+" dupe "+d["dupe"])}/'>{e(d['dupe'])}</a></b><div class=meta>{e(d['notes'])}</div></td>
<td>{(f"<b>${d['price']:.2f}</b> ({e(d['size'])}) {ext_a(d['url'], 'Perfumania')}<div class=meta>checked {upd_h}</div>") if d['price'] else "<span class=meta>Not tracked yet — price check coming</span>"}</td>
<td class=meta>{' '.join((f'<a href="{e(affiliate_url(s))}" rel="sponsored nofollow noopener" target="_blank">[{i+1}]</a>' if is_perfumania(s) else f"<a href='{e(s)}' rel=noopener target=_blank>[{i+1}]</a>") for i,s in enumerate(d['sources']))}</td></tr>""" for d in D["dupes"])
faq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the best dupe for {d['original']}?","acceptedAnswer":{"@type":"Answer","text":f"{d['dupe']} is a widely cited alternative to {d['original']} ({d['notes']})."+(f" It was ${d['price']:.2f} for {d['size']} at Perfumania as of {upd:%Y-%m-%d}." if d['price'] else "")}} for d in D["dupes"]]}
page("dupes/index.html",f"Best Designer Fragrance Dupes {upd.year}: {len(D['dupes'])} Clones With Live Prices | {NAME}",
 "Creed Aventus, Baccarat Rouge 540, Angels' Share, Sauvage Elixir and more: the most-cited affordable dupes, with today's prices and sources.",
 f"<h1>Designer fragrance dupes directory</h1><p class='sub'>Popular designer → affordable alternative pairs, cited from fragrance community rankings. Dupes are legally sold originals \"inspired by\" a scent — not counterfeits.</p><table><thead><tr><th>Designer original</th><th>Dupe</th><th>Today's price</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>{signup}",[faq])
# gender/category pages
for g,label in [("men","Men's Cologne"),("women","Women's Perfume"),("unisex","Unisex Fragrance")]:
    ds=[d for d in deals if d["gender"]==g]
    if not ds: continue
    page(f"{g}/index.html",f"{label} Deals Today ({upd:%b %-d}) | {NAME}",f"{len(ds)} discounted authentic {label.lower()} deals, checked daily.",
      f"<h1>{label} deals</h1><p class='sub'>{len(ds)} live · checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{signup}",[itemlist(ds,label+" deals")])
brands=sorted({d["brand"] for d in deals})
for b in brands:
    ds=[d for d in deals if d["brand"]==b]
    page(f"brands/{slug(b)}/index.html",f"{b} Fragrance Deals & Discounts Today | {NAME}",f"Today's best {b} perfume and cologne deals at authorized retailers, price-checked daily.",
      f"<h1>{e(b)} deals</h1><p class='sub'>checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{signup}",[itemlist(ds,b+" deals")])
page("brands/index.html",f"Fragrance Deals by Brand | {NAME}","Browse today's designer fragrance deals by brand.",
 "<h1>Deals by brand</h1><div class='chips'>"+"".join(f"<a href='{PREFIX}/brands/{slug(b)}/'>{e(b)}</a>" for b in brands)+"</div>")
page("sponsor/index.html",f"Sponsor {NAME} / Feature Your Brand","Reach fragrance shoppers actively looking to buy. Featured listings and newsletter sponsorships.",
 f"""<h1>Feature your fragrance brand</h1><p class='sub'>Put your scent in front of shoppers who are ready to buy.</p>
<div class='box'><h2 style='margin-top:0'>Options</h2><ul><li><b>Featured deal</b> — pinned at the top of the homepage for 7 days, clearly labeled "Sponsored".</li>
<li><b>Newsletter sponsor</b> — one slot in the daily email.</li><li><b>Dupe spotlight</b> — your house featured on the dupes directory (must be an original composition, not a counterfeit).</li></ul>
<p>Rules: authentic products only, every sponsored placement labeled, no fake reviews.</p>
<p>Contact: <a href="mailto:hello@scentdealsdaily.com">hello@scentdealsdaily.com</a> (pricing on request).</p></div>""")
page("disclosure/index.html",f"Affiliate Disclosure | {NAME}","How ScentDealsDaily makes money.",
 """<h1>Affiliate disclosure</h1><div class='box'><p>We may earn a commission when you buy through our links, at no extra cost to you.</p>
<p>Some links on this site are affiliate links. If you buy through them, we may earn a commission at no extra cost to you. This never changes which deals we list or how they're ranked (by % off).</p>
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
    full=f"{d['brand']} {d['name']}"; s=slug(full); KW+= [f"{full.lower()} cheapest price",f"{full.lower()} sale",f"{full.lower()} {d['size'].lower()} deal"]
    gl={"men":"men's cologne","women":"women's perfume","unisex":"unisex fragrance"}[d['gender']]
    others=[x for x in deals if x['gender']==d['gender'] and x['id']!=d['id']][:4]
    qs=[(f"What is the cheapest price for {full} right now?",f"As of {upd_h}, the lowest price we verified is ${d['price']:.2f} for {d['size']} at {d['retailer']}, {d['pct_off']}% below {('the $%.2f at %s' % (d['was'],d['was_label'])) if d.get('was_label') else ('its listed $%.2f' % d['was'])}."),
        (f"Is {full} on sale?",f"{d['retailer']} has it at ${d['price']:.2f} versus ${d['was']:.2f} {('at '+d['was_label']) if d.get('was_label') else 'listed compare-at'}. We re-check daily and remove it when the deal ends."),
        (f"Is the {d['retailer']} {full} authentic?",f"{d['retailer']} is a long-established US fragrance chain selling genuine designer brands. We exclude marketplace sellers and tester listings."),
        (f"How much do I save per ounce?",f"At ${d['price']:.2f} for {d['size']}, you save ${d['was']-d['price']:.2f} versus the listed price.")]
    body=(f"<h1>{e(full)} {e(d['size'])}: cheapest price today</h1><p class='sub'>Lowest verified price: <b class='price'>${d['price']:.2f}</b> <span class='was'>${d['was']:.2f}</span> <span class='badge'>-{d['pct_off']}%</span> at {e(d['retailer'])} · checked {upd_h}</p>"
      +buy(d['url'],d['retailer'])
      +f"<div class='box' style='display:flex;gap:16px;flex-wrap:wrap'><img src='{e(d['image'] or '')}' alt='{e(full)}' width=220 height=220 style='object-fit:contain'><div style='flex:1;min-width:220px'><h2 style='margin-top:0'>Price comparison</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table><p class=meta>More retailers are added as we verify them. We never list unverified prices.</p></div></div>"
      +f"<p>{e(full)} is one of today's best {gl} deals: {d['pct_off']}% off the listed price, a {d['type'].lower() or 'fragrance'} from {e(d['brand'])} (<a href='{PREFIX}/brands/{slug(d['brand'])}/'>all {e(d['brand'])} deals</a>).</p>"
      +faqhtml(qs)+"<h2>Similar deals today</h2><div class='grid'>"+"".join(card(x) for x in others)+"</div>"+signup)
    page(f"fragrance/{s}/index.html",f"{full} {d['size']} Cheapest Price ${d['price']:.2f} ({d['pct_off']}% Off) | Sale {upd:%b %Y}",
      f"{full} {d['size']} for ${d['price']:.2f} at {d['retailer']} (was ${d['was']:.2f}). Authentic, price-checked {upd:%b %-d, %Y}.",body,
      [prod_ld(f"{full} {d['size']}",d['brand'],d['image'],d['price'],d['url'],d['retailer']),faqld(qs)])
for d in D["dupes"]:
    s=slug(f"{d['original']} dupe {d['dupe']}"); o=d['original']
    KW+=[f"{o.lower()} dupe",f"best cheap {o.lower()} dupe {upd.year}",f"{d['dupe'].lower()} vs {o.lower()}"]
    pr=f"${d['price']:.2f} for {d['size']} at {d['retailer']}" if d['price'] else "not yet price-verified by us"
    qs=[(f"What is the best cheap {o} dupe in {upd.year}?",f"{d['dupe']} is one of the most-cited affordable alternatives to {o}: {d['notes']}. Today: {pr}."),
        (f"Does {d['dupe']} smell like {o}?",f"Community rankings rate it as close ({d['notes']}). It is an original 'inspired by' fragrance, not a counterfeit; expect differences in the dry-down."),
        (f"Where can I buy {d['dupe']} cheapest?",f"The lowest price we verified is {pr}" + (f" (checked {upd_h})." if d['price'] else ". Check back; we add prices only after verifying them."))]
    rel=[x for x in D['dupes'] if x is not d][:5]
    body=(f"<h1>Best {e(o)} dupe: {e(d['dupe'])}</h1><p class='sub'>{e(d['notes'])} · {('<b class=price>$%.2f</b> today at %s' % (d['price'],e(d['retailer']))) if d['price'] else 'price not verified yet'}</p>"
      +(buy(d['url'],d['retailer']) if d['price'] else "")
      +f"<div class='box'><h2 style='margin-top:0'>{e(o)} vs {e(d['dupe'])}</h2><table><thead><tr><th></th><th>{e(o)}</th><th>{e(d['dupe'])}</th></tr></thead><tbody><tr><td>Price</td><td>{e(d.get('original_price') or 'varies')}</td><td>{('$%.2f (%s)' % (d['price'],e(d['size']))) if d['price'] else '—'}</td></tr><tr><td>Profile</td><td colspan=2>{e(d['notes'])}</td></tr><tr><td>Sources</td><td colspan=2>{' '.join((f'<a href="{e(affiliate_url(x))}" rel="sponsored nofollow noopener" target="_blank">[{i+1}]</a>' if is_perfumania(x) else f'<a href={e(x)} rel=noopener target=_blank>[{i+1}]</a>') for i,x in enumerate(d['sources']))}</td></tr></tbody></table></div>"
      +((f"<div class='box'><h2 style='margin-top:0'>Where to buy {e(d['dupe'])} cheapest</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table></div>") if d.get('comps') else "")+faqhtml(qs)+"<h2>More dupes</h2><div class='chips'>"+"".join(f"<a href='{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/'>{e(x['original'])} → {e(x['dupe'])}</a>" for x in rel)+f"</div><p><a href='{PREFIX}/dupes/'>All dupes</a></p>"+signup)
    lds=[faqld(qs)]+([prod_ld(d['dupe'],d['dupe'].split()[0],d.get('image'),d['price'],d['url'],d['retailer'])] if d['price'] else [])
    page(f"dupe/{s}/index.html",f"Best {o} Dupe {upd.year}: {d['dupe']}"+(f" ${d['price']:.2f}" if d['price'] else ""),
      f"{d['dupe']} vs {o}: how close it is, today's cheapest price, and where to buy authentic.",body,lds)
# rewrite sitemap with new pages + keyword list + IndexNow key
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
KEY=hashlib.md5(b"scentdealsdaily-indexnow").hexdigest(); open(f"{OUT}/{KEY}.txt","w").write(KEY)
open(f"{ROOT}/docs/keywords.txt","w").write("\n".join(KW)+"\n")
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Per-product & per-dupe pages\n"+"\n".join(u for u in PAGES if "/fragrance/" in u or "/dupe/" in u)+"\n")
print(len(PAGES),"pages total;",len(KW),"keywords")
