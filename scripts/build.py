#!/usr/bin/env python3
"""Render data/deals.json -> static site in site/. Usage: SITE_URL=https://... python3 scripts/build.py"""
import json, os, html, re, datetime, urllib.parse, shutil, tempfile
import links
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=f"{ROOT}/site"
# site/ is wiped and regenerated; keep promo videos in site/media across that rebuild.
_media_tmp=None
if os.path.isdir(f"{OUT}/media"):
    _media_tmp=tempfile.mkdtemp(prefix="sdd-media-")
    shutil.copytree(f"{OUT}/media", f"{_media_tmp}/media")
if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(OUT, exist_ok=True)
BASE=os.environ.get("SITE_URL","https://scentdealsdaily.com").rstrip("/")
_b=urllib.parse.urlsplit(BASE); BASE=urllib.parse.urlunsplit((_b.scheme,_b.netloc.lower(),_b.path,"",""))  # CI passes "Aministan.github.io"; canonicals, sitemap and IndexNow need the lowercase host
PREFIX=os.environ.get("PATH_PREFIX","")  # custom domain scentdealsdaily.com serves from the root (was /scentdealsdaily on aministan.github.io)
FEED_HREF=f"{BASE}{PREFIX}/feed.xml"
CUSTOM_DOMAIN=os.environ.get("CUSTOM_DOMAIN","scentdealsdaily.com")  # written to site/CNAME so every rebuild keeps the GitHub Pages custom domain
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
def is_cj(url):
    """Any CJ click URL for this publisher (click-101905413-<adid>), whatever the domain or ad id."""
    return isinstance(url,str) and "click-101905413-" in url
def is_affiliate(url):
    return is_perfumania(url) or is_fragranceshop(url) or is_cj(url)
# Page context for the CJ shopper id. Set with use_sid() before a page's HTML is built.
CTX={"type":"site","slug":""}
def _sid_part(s):
    return re.sub(r"-{2,}","-",re.sub(r"[^a-z0-9-_]+","-",(s or "").lower())).strip("-")
def use_sid(typ, slug=""):
    CTX["type"]=_sid_part(typ) or "site"
    CTX["slug"]=_sid_part(slug)
def make_sid(placement):
    """<pagetype>-<slug>-<placement>, charset [a-z0-9-_], at most 64 characters."""
    typ,slug,place=CTX["type"],CTX["slug"],_sid_part(placement) or "link"
    sid="-".join(p for p in (typ,slug,place) if p)
    if len(sid)<=64: return sid
    budget=64-len(typ)-len(place)-2
    cut=""
    if slug and budget>=1:
        cut=slug[:budget].rstrip("-")
        if len(slug)>budget and "-" in cut: cut=cut.rsplit("-",1)[0]
        cut=cut.strip("-")
    sid="-".join(p for p in (typ,cut,place) if p)
    return sid[:64].strip("-")
def add_sid(url, sid):
    """Put sid on the CJ click URL. Leave every other query parameter, including url=, byte-for-byte."""
    sid_q=urllib.parse.quote(sid, safe="-_")
    frag=""
    if "#" in url:
        url,frag=url.split("#",1); frag="#"+frag
    if "?" not in url: return url+"?sid="+sid_q+frag
    base,query=url.split("?",1)
    parts=[p for p in query.split("&") if p and not p.startswith("sid=")]
    return base+"?sid="+sid_q+(("&"+("&".join(parts))) if parts else "")+frag
def affiliate_url(url, placement="link"):
    """CJ deep link for Perfumania and FragranceShop, with a shopper id. Other retailers stay as-is."""
    if not isinstance(url,str) or not url: return url
    sid=make_sid(placement)
    if is_cj(url): return add_sid(url, sid)
    cj = CJ_PM if is_perfumania(url) else CJ_FS if is_fragranceshop(url) else None
    if not cj: return url
    p=urllib.parse.urlparse(url)
    base=cj+"?sid="+urllib.parse.quote(sid, safe="-_")
    if (p.path or "") in ("","/") and not p.query and not p.fragment: return base
    return base+"&url="+urllib.parse.quote(url,safe="")
def ext_a(url, inner, cls="", style="", placement="link"):
    href=e(affiliate_url(url, placement))
    extra=(f' class="{cls}"' if cls else "")+(f" style='{style}'" if style else "")
    # Affiliate anchors are for a person clicking. No prefetch, prerender, or dns-prefetch.
    if is_affiliate(url) or links.is_tracking_url(url):
        return f'<a{extra} rel="nofollow sponsored noopener" target="_blank" href="{href}">{inner}</a>'
    return f"<a{extra} rel='nofollow sponsored noopener' target=_blank href='{href}'>{inner}</a>"
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")
import unicodedata
BRAND_CANON={"Lancome":"Lancôme"}  # Perfumania uses both spellings; one brand page
def canon(b): return BRAND_CANON.get(b,b)
def bslug(b): return slug(unicodedata.normalize("NFKD",canon(b)).encode("ascii","ignore").decode())
def sz(size): return re.sub(r"\s+"," ",size or "").strip().rstrip(".")
def fullname(d):
    """Display name without a doubled brand ("Azzaro Azzaro Cologne" -> "Azzaro Cologne"). URLs keep brand+name slugs."""
    b,n=d['brand'],d['name']; cb=canon(b)
    if n.lower().startswith(b.lower()+" "): return cb+n[len(b):]
    if n.lower().startswith(cb.lower()+" "): return n
    last=cb.split()[-1]
    if " " in cb and n.lower().startswith(last.lower()+" "): return cb+n[len(last):]  # Hugo Boss + "Boss Bottled ..." -> "Hugo Boss Bottled ..."
    return f"{cb} {n}"
def oz(size):
    m=re.match(r"\s*([0-9]*\.?[0-9]+)\s*oz",size or "",re.I); return float(m.group(1)) if m else None
def per_oz(d):
    o=oz(d.get('size')); return d['price']/o if o else None
def money(x): return f"${x:,.2f}"
def fit(cands,n=60):
    """First candidate that fits n chars (search-result width), else the shortest."""
    cands=[c for c in cands if c]
    return next((c for c in cands if len(c)<=n),min(cands,key=len))
def clip(t,n=160):
    """Trim a meta description at a word boundary so it isn't cut mid-word in results."""
    if len(t)<=n: return t
    t=t[:n-1].rsplit(" ",1)[0].rstrip(",;:(–-. ")
    return t+"."
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
table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;padding:10px;border-bottom:1px solid #eee;vertical-align:top}
.chips a{display:inline-block;margin:3px;padding:4px 10px;border-radius:99px;background:#fff;border:1px solid #e3ddd6;text-decoration:none;font-size:14px}
footer{max-width:1100px;margin:20px auto;padding:16px;font-size:13px;color:#6f6976}
.nl{margin:18px 0}.nl-foot{margin:0 0 12px}
@media(max-width:640px){table,thead,tbody,tr,td{display:block}thead{display:none}td{border:0;padding:4px 10px}tr{border-bottom:1px solid #eee;padding:8px 0}}"""
BREVO_URL="https://dc62f1d4.sibforms.com/serve/MUIFAEr2_FjNas7tKaQpb8Gb1G8G8lAWo4YUlMQLlesHgqoeXDeb81p6QoFTA97ntOQFoJ4oeYqYMvNLQ_abdWQ7yXLxfV3Ip6_yAkBb31h5wt_6nN7ia5t-doG3uLTnPam6d-V-faigM0xHfhmkEvb_KToQHCq2QIwPP4u-dsOd3SyYzJzE8_dUkbPBtLTO2DT2MnTeld3EP66vtQ=="
# Brevo's embed uses fixed ids, so the full form is included once per page. The footer is a link to the hosted form.
BREVO_HEAD="""<link rel="stylesheet" href="https://sibforms.com/forms/end-form/build/sib-styles.css">
<style>
  @font-face {font-display:block;font-family:Roboto;src:url(https://assets.brevo.com/font/Roboto/Latin/normal/normal/7529907e9eaf8ebb5220c5f9850e3811.woff2) format("woff2"),url(https://assets.brevo.com/font/Roboto/Latin/normal/normal/25c678feafdc175a70922a116c9be3e7.woff) format("woff")}
  @font-face {font-display:fallback;font-family:Roboto;font-weight:600;src:url(https://assets.brevo.com/font/Roboto/Latin/medium/normal/6e9caeeafb1f3491be3e32744bc30440.woff2) format("woff2"),url(https://assets.brevo.com/font/Roboto/Latin/medium/normal/71501f0d8d5aa95960f6475d5487d4c2.woff) format("woff")}
  @font-face {font-display:fallback;font-family:Roboto;font-weight:700;src:url(https://assets.brevo.com/font/Roboto/Latin/bold/normal/3ef7cf158f310cf752d5ad08cd0e7e60.woff2) format("woff2"),url(https://assets.brevo.com/font/Roboto/Latin/bold/normal/ece3a1d82f18b60bcce0211725c476aa.woff) format("woff")}
  :where(.sib-form-message-panel){display:none}
  :where(.sib-form-message-panel .sib-notification__icon){width:20px;height:20px}
  #sib-container input:-ms-input-placeholder{text-align:left;color:#8d8791}
  #sib-container input::placeholder,#sib-container textarea::placeholder{text-align:left;color:#8d8791;font-family:inherit}
  #sib-container a{text-decoration:underline;color:#6b2d5c}
  .sib-form{padding:0;background:transparent;text-align:left}
  #sib-form{display:block;margin:0}
  #sib-container{max-width:540px;width:100%;box-sizing:border-box}
  #sib-container .entry__field{display:block}
  #sib-container input.input{width:100%;box-sizing:border-box;padding:11px 12px;border:1px solid #d9d3cc;border-radius:10px;font:16px/1.4 inherit;color:#1d1b20;background:#fff}
  #sib-container .sib-form-block__button{font-family:inherit;cursor:pointer;width:auto;min-width:140px}
  .input--hidden{position:absolute;left:-9999px;height:0;width:0;opacity:0}
  @media(max-width:640px){#sib-container{padding-left:12px;padding-right:12px}#sib-container .sib-form-block__button{width:100%}}
</style>"""
BREVO_FORM=f"""<section class="nl" id="newsletter" aria-label="Weekly fragrance deals"><div class="sib-form" style="text-align:left;background:transparent">
<div id="sib-form-container" class="sib-form-container">
<div id="error-message" class="sib-form-message-panel" style="font-size:15px;text-align:left;color:#661d1d;background-color:#ffeded;border-color:#ff4949;border-radius:10px;max-width:540px"><div class="sib-form-message-panel__text sib-form-message-panel__text--center"><svg viewBox="0 0 512 512" class="sib-icon sib-notification__icon"><path d="M256 40c118.621 0 216 96.075 216 216 0 119.291-96.61 216-216 216-119.244 0-216-96.562-216-216 0-119.203 96.602-216 216-216m0-32C119.043 8 8 119.083 8 256c0 136.997 111.043 248 248 248s248-111.003 248-248C504 119.083 392.957 8 256 8zm-11.49 120h22.979c6.823 0 12.274 5.682 11.990 12.5l-7 168c-.268 6.428-5.556 11.5-11.99 11.5h-8.979c-6.433 0-11.722-5.073-11.99-11.5l-7-168c-.283-6.818 5.167-12.5 11.99-12.5zM256 340c-15.464 0-28 12.536-28 28s12.536 28 28 28 28-12.536 28-28-12.536-28-28-28z"/></svg><span class="sib-form-message-panel__inner-text">Your subscription could not be saved. Please try again.</span></div></div>
<div id="success-message" class="sib-form-message-panel" style="font-size:15px;text-align:left;color:#085229;background-color:#e7faf0;border-color:#13ce66;border-radius:10px;max-width:540px"><div class="sib-form-message-panel__text sib-form-message-panel__text--center"><svg viewBox="0 0 512 512" class="sib-icon sib-notification__icon"><path d="M256 8C119.033 8 8 119.033 8 256s111.033 248 248 248 248-111.033 248-248S392.967 8 256 8zm0 464c-118.664 0-216-96.055-216-216 0-118.663 96.055-216 216-216 118.664 0 216 96.055 216 216 0 118.663-96.055 216-216 216zm141.63-274.961L217.15 376.071c-4.705 4.667-12.303 4.637-16.97-.068l-85.878-86.572c-4.667-4.705-4.637-12.303.068-16.97l8.52-8.451c4.705-4.667 12.303-4.637 16.970.068l68.976 69.533 163.441-162.13c4.705-4.667 12.303-4.637 16.97.068l8.451 8.52c4.668 4.705 4.637 12.303-.068 16.97z"/></svg><span class="sib-form-message-panel__inner-text">Check your inbox to confirm your subscription.</span></div></div>
<div id="sib-container" class="sib-container--large sib-container--vertical" style="max-width:540px;text-align:left;background:#fff;border:1px solid #ece7e1;border-radius:14px;padding:8px 16px 16px">
<form id="sib-form" method="POST" action="{BREVO_URL}" data-type="subscription">
<div style="padding:8px 0"><div class="sib-form-block" style="font-size:20px;font-weight:700;text-align:left;color:#1d1b20;background:transparent"><p style="margin:0">Weekly fragrance deals</p></div></div>
<div style="padding:0 0 8px"><div class="sib-form-block" style="font-size:15px;text-align:left;color:#5f5a66;background:transparent"><div class="sib-text-form-block"><p style="margin:0">The best authentic fragrance price drops, every Friday. Unsubscribe anytime.</p></div></div></div>
<div style="padding:8px 0"><div class="sib-input sib-form-block"><div class="form__entry entry_block"><div class="form__label-row"><label class="entry__label" style="font-weight:600;text-align:left;font-size:14px;color:#5f5a66" for="EMAIL" data-required="*">Enter your email address to subscribe</label><div class="entry__field"><input class="input" type="text" id="EMAIL" name="EMAIL" autocomplete="off" inputmode="email" autocapitalize="off" spellcheck="false" placeholder="you@email.com" data-required="true" required></div></div><label class="entry__error entry__error--primary" style="font-size:14px;text-align:left;color:#661d1d;background-color:#ffeded;border-color:#ff4949;border-radius:10px"></label></div></div></div>
<div style="padding:8px 0"><div class="sib-form-block" style="text-align:left"><button class="sib-form-block__button sib-form-block__button-with-loader" style="font-size:16px;font-weight:700;color:#fff;background:#6b2d5c;border:0;border-radius:10px;padding:11px 16px" form="sib-form" type="submit"><svg class="icon clickable__icon progress-indicator__icon sib-hide-loader-icon" viewBox="0 0 512 512"><path d="M460.116 373.846l-20.823-12.022c-5.541-3.199-7.54-10.159-4.663-15.874 30.137-59.886 28.343-131.652-5.386-189.946-33.641-58.394-94.896-95.833-161.827-99.676C261.028 55.961 256 50.751 256 44.352V20.309c0-6.904 5.808-12.337 12.703-11.982 83.556 4.306 160.163 50.864 202.11 123.677 42.063 72.696 44.079 162.316 6.031 236.832-3.14 6.148-10.75 8.461-16.728 5.01z"/></svg>Subscribe</button></div></div>
<input type="text" name="email_address_check" value="" class="input--hidden"><input type="hidden" name="locale" value="en">
</form></div></div></div></section>"""
BREVO_JS="""<script>
  window.REQUIRED_CODE_ERROR_MESSAGE = 'Please choose a country code';
  window.LOCALE = 'en';
  window.EMAIL_INVALID_MESSAGE = window.SMS_INVALID_MESSAGE = "The information provided is invalid. Please review the field format and try again.";
  window.REQUIRED_ERROR_MESSAGE = "This field cannot be left blank. ";
  window.GENERIC_INVALID_MESSAGE = "The information provided is invalid. Please review the field format and try again.";
  window.INVALID_NUMBER = "The information provided is invalid. Please review the field format and try again.";
  window.INVALID_DATE = "Please enter a valid date";
  window.REQUIRED_MULTISELECT_MESSAGE = 'Please select at least 1 option';
  window.translation = {common:{selectedList:'{quantity} list selected',selectedLists:'{quantity} lists selected',selectedOption:'{quantity} selected',selectedOptions:'{quantity} selected'}};
  var AUTOHIDE = Boolean(0);
</script>
<script defer src="https://sibforms.com/forms/end-form/build/main.js"></script>"""
NL_FOOT=f'<p class="nl-foot"><a href="{BREVO_URL}">Weekly fragrance deals</a>, every Friday.</p>'
TITLES=set()
def page(path,title,desc,body,jsonld=None,index=True,image=None):
    if title in TITLES: title=f"{title} ({path.split('/')[0].title()})"
    TITLES.add(title); desc=clip(desc)
    url=f"{BASE}{PREFIX}/{path}".replace("/index.html","/")
    ld="".join(f'<script type="application/ld+json">{json.dumps(j,ensure_ascii=False)}</script>' for j in (jsonld or []))
    p=PREFIX
    has_form='id="sib-form"' in body
    brevo_head=BREVO_HEAD if has_form else ""
    brevo_js=BREVO_JS if has_form else ""
    robots="" if index else '<meta name="robots" content="noindex">'
    if image:
        img=image if image.startswith("http") else f"{BASE}{PREFIX}{image}"
        social=(f'<meta property="og:image" content="{e(img)}"><meta property="og:image:width" content="1000"><meta property="og:image:height" content="1500">'
                f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{e(img)}">')
    else:
        social='<meta name="twitter:card" content="summary">'
    doc=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="GASeKy1uEWpsrSn1II701znBYlw6mBhAwvimW0Yi8Io" />
<meta name="google-site-verification" content="AnNdRzKxRNra8nkj3gri7zC9kJYJ-aZehksWkrfImx4" />
<meta name='impact-site-verification' value='6f939439-73de-427f-89fc-c18dc2f9f64d'>
<meta name="p:domain_verify" content="7833fa67293af531c9de288142c68c3c"/>
{robots}<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="ScentDealsDaily" href="{FEED_HREF}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}"><meta property="og:type" content="website">
{social}<link rel="preconnect" href="https://cdn.shopify.com"><style>{CSS}</style>{brevo_head}{ld}</head><body>
<header><a class="logo" href="{p}/">Scent<span>Deals</span>Daily</a><nav><a href="{p}/">Today's deals</a><a href="{p}/dupes/">Dupes</a><a href="{p}/men/">Men</a><a href="{p}/women/">Women</a><a href="{p}/brands/">Brands</a><a href="{p}/sponsor/">Sponsor</a></nav></header>
<main>{body}</main><footer>{NL_FOOT}<p>We may earn a commission when you buy through our links, at no extra cost to you. Affiliate links go to Perfumania and FragranceShop.</p>
<p><b>Affiliate disclosure:</b> some links may earn us a commission at no cost to you. <a href="{p}/disclosure/">Details</a>.
We list only authorized or long-established retailers, never gray-market marketplaces. Prices change fast; each deal shows when we last checked it. Not affiliated with any brand.</p>
<p>© {upd.year} {NAME} · <a href="{p}/gifts/">Holiday gifts</a> · <a href="{p}/llms.txt">llms.txt</a> · <a href="{p}/sitemap.xml">sitemap</a></p>
<p><img src="https://hits.sh/scentdealsdaily.com.svg?label=visitors" alt="visitor count" loading="lazy" height="20"></p></footer>{brevo_js}<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "5bfd6f8b561c42e982e52bf2a553ff60"}}'></script><!-- End Cloudflare Web Analytics --></body></html>"""
    fp=f"{OUT}/{path}"; os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w").write(doc)
    if not index: return
    PAGES.append(url)
    k=feed_kind(path)
    if k: FEED.append((k,title,url,desc))
PAGES=[]
FEED=[]  # (kind, title, url, plain meta description) for deal and comparison pages
def feed_kind(path):
    if path.startswith("fragrance/"): return "deal"
    if path.startswith("vs/") or path.startswith("best/"): return "compare"
    if path.startswith("dupes/") and path!="dupes/index.html": return "hub"
    if path.startswith("dupe/"): return "dupe"
    return None
def also_line(d):
    a=d.get("also")
    if not a or a.get("price") is None or not a.get("url"): return ""
    return f"<div class='also'>also at {ext_a(a['url'], e(a['retailer']), placement='also')} · ${a['price']:.2f}</div>"
def card(d,eager=False):
    ld='fetchpriority="high"' if eager else 'loading="lazy"'
    return f"""<article class="card"><img {ld} decoding="async" src="{e(d['image'] or '')}" alt="{e(fullname(d))}" width="400" height="400">
<div><span class="badge">-{d['pct_off']}%</span></div><div class="brand">{e(canon(d['brand']))}</div><div class="nm"><a href="{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/">{e(d['name'])}</a> · {e(d['size'])}</div>
<div><span class="price">${d['price']:.2f}</span><span class="was">${d['was']:.2f}</span></div>
<div class="meta">at {e(d['retailer'])} · checked {upd_h} · {('crossed-out = price at '+e(d['was_label'])) if d.get('was_label') else '"was" = retailer\'s listed compare-at price'}</div>
{also_line(d)}
{ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn", placement="grid")}</article>"""
def conc_name(t):
    """Concentration label from the stored type. Only the values we already record."""
    low=(t or "").strip().lower()
    if not low: return ""
    if low=="parfum" or low.startswith("parfum "): return "Parfum"
    if "parfum" in low: return "Eau de Parfum"
    if "toilette" in low: return "Eau de Toilette"
    return re.sub(r"\s+"," ",t.strip())
def check_day(raw):
    """Date of a price check. Unparseable notes fall back to the file's updated date."""
    m=re.match(r"(\d{4}-\d{2}-\d{2})", str(raw or ""))
    return m.group(1) if m else upd.strftime("%Y-%m-%d")
PRICE_UNTIL=(upd+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
def product_description(d):
    """Description from brand, name, concentration, size, and gender. No claims we did not check."""
    if d.get("brand") and d.get("name"):
        short=re.sub(r" (Cologne|Perfume|Unisex Fragrance)$","",fullname(d)).strip()
    else:
        short=(d.get("dupe") or d.get("name") or "").strip()
    conc=conc_name(d.get("type"))
    size=sz(d.get("size") or "")
    bits=[short]
    if conc and conc.lower() not in short.lower(): bits.append(conc)
    if size and size not in short: bits.append(size)
    text=" ".join(b for b in bits if b)
    if d.get("gender")=="men": text+=" for men"
    elif d.get("gender")=="women": text+=" for women"
    elif d.get("gender")=="unisex": text+=" for men and women"
    return text+", compared across authorized retailers."
def offer_rows(d):
    rows=[c for c in (d.get("comps") or []) if isinstance(c.get("price"),(int,float)) and not isinstance(c.get("price"),bool) and c.get("url") and c.get("retailer")]
    if rows: return rows
    if isinstance(d.get("price"),(int,float)) and not isinstance(d.get("price"),bool) and d.get("url") and d.get("retailer"):
        return [{"retailer":d["retailer"],"price":d["price"],"url":d["url"],"checked":d.get("checked")}]
    return []
def offer_node(c, d):
    """One store's checked price. Shipping and returns stay off: we are not the seller and do not have that data."""
    avail="https://schema.org/InStock" if d.get("in_stock") is not False else "https://schema.org/OutOfStock"
    return {"@type":"Offer","price":f"{c['price']:.2f}","priceCurrency":"USD","availability":avail,
            "url":links.retailer_url(c["url"]) or c["url"],"seller":{"@type":"Organization","name":c["retailer"]},
            "priceValidUntil":PRICE_UNTIL,"validFrom":check_day(c.get("checked") or d.get("checked"))}
def aggregate_offer(d):
    nodes=[offer_node(c,d) for c in offer_rows(d)]
    if not nodes: return None
    prices=[float(o["price"]) for o in nodes]
    return {"@type":"AggregateOffer","lowPrice":f"{min(prices):.2f}","highPrice":f"{max(prices):.2f}",
            "offerCount":len(nodes),"priceCurrency":"USD","offers":nodes}
def prod_ld(d, name=None, brand=None):
    if name is None:
        name=(f"{fullname(d)} {d.get('size') or ''}".strip() if d.get("brand") and d.get("name") else (d.get("dupe") or d.get("name") or ""))
    if brand is None:
        brand=canon(d["brand"]) if d.get("brand") else (d.get("dupe") or "").split(" ")[0]
    product={"@context":"https://schema.org","@type":"Product","name":name,"description":product_description(d)}
    if brand: product["brand"]={"@type":"Brand","name":brand}
    if d.get("image"): product["image"]=d["image"]
    offers=aggregate_offer(d)
    if offers: product["offers"]=offers
    return product
def itemlist(ds,name):
    items=[]
    for i,d in enumerate(ds):
        item=prod_ld(d, name=f"{fullname(d)} {d['size']}", brand=canon(d["brand"]))
        item.pop("@context",None)
        items.append({"@type":"ListItem","position":i+1,"item":item})
    return {"@context":"https://schema.org","@type":"ItemList","name":name,"itemListElement":items}
deals=D["deals"]
BYID={d['id']:d for d in deals}
# ---- roundups (/best/...) and dupe hubs (/dupes/<hub>/): data-driven so they survive the daily rebuild ----
U50="the price must be under $50 right now"
ROUNDUPS=[r for r in [
  {"slug":"cologne-deals-under-50","title":"Best Cologne Deals Under $50","noun":"cologne","who":"men's and unisex","scope":"under $50","rule":U50,"items":[d for d in deals if d['gender'] in ('men','unisex') and d['price']<50]},
  {"slug":"perfume-deals-under-50","title":"Best Perfume Deals Under $50","noun":"perfume","who":"women's and unisex","scope":"under $50","rule":U50,"items":[d for d in deals if d['gender'] in ('women','unisex') and d['price']<50]},
  {"slug":"fragrance-deals-under-30","title":"Best Fragrance Deals Under $30","noun":"fragrance","who":"men's, women's and unisex","scope":"under $30","rule":"the price must be under $30 right now",
   "lead":"Full-size designer bottles you can buy for less than $30 today, mixed across men's, women's and unisex picks.","items":[d for d in deals if d['price']<30]},
  {"slug":"luxury-fragrance-deals","title":"Best Luxury Fragrance Deals","noun":"luxury fragrance","who":"prestige","scope":"with a $120+ list price","rule":"the bottle's listed price (or another authorized retailer's price) must be $120 or more",
   "lead":"Prestige perfumes and colognes that normally list for $120 or more, discounted at authorized retailers today. Good for gifts or a bottle you would not usually pay full price for.","items":[d for d in deals if d['was']>=120]},
 ]+[dict(r,items=[BYID[i['id']] for i in r['items'] if i['id'] in BYID],notes={i['id']:i['notes'] for i in r['items']}) for r in CFG.get("roundups",[])] if len(r["items"])>=3]
def roundups_of(d): return [r for r in ROUNDUPS if d in r['items']]
HUBS=[]
for h in CFG.get("hubs",[]):
    ms=[x for x in D["dupes"] if any(m in x["original"] for m in h["match"])]
    if len(ms)>=2: HUBS.append(dict(h,items=ms,topic=h["title"].replace("Best ","").replace(" Dupes","")))
def hub_of(d): return next((h for h in HUBS if d in h["items"]),None)
VS=[dict(v,A=BYID[v['a']],B=BYID[v['b']]) for v in CFG.get("vs",[]) if v['a'] in BYID and v['b'] in BYID]
def vs_of(d): return [v for v in VS if d is v['A'] or d is v['B']]
def bestchips(): return ("<section class='box'><h2 style='margin-top:0'>Shop by budget, scent &amp; dupe guides</h2><div class='chips'>"
    +"".join(f"<a href='{PREFIX}/best/{r['slug']}/'>{e(r['title'])}</a>" for r in ROUNDUPS)
    +"".join(f"<a href='{PREFIX}/dupes/{h['slug']}/'>{e(h['title'])}</a>" for h in HUBS)
    +"".join(f"<a href='{PREFIX}/vs/{v['slug']}/'>{e(v['title'])}</a>" for v in VS)+"</div></section>") if (ROUNDUPS or HUBS or VS) else ""
SEO_GIFTS=[
 ("perfume-gifts-for-her-under-50","Perfume gifts for her under $50"),
 ("best-mens-cologne-under-40","Best men's cologne under $40"),
 ("stocking-stuffer-minis","Stocking stuffer fragrance minis & travel sizes"),
 ("holiday-gift-sets","Fragrance gift sets for the holidays"),
]
use_sid("home")
page("index.html",fit([f"Perfume & Cologne Deals Today: Up to {max(d['pct_off'] for d in deals)}% Off | {NAME}",f"Fragrance Deals Today: Up to {max(d['pct_off'] for d in deals)}% Off | {NAME}"]),
 f"{len(deals)} verified deals on authentic designer perfume & cologne from ${min(d['price'] for d in deals):.2f}, up to {max(d['pct_off'] for d in deals)}% off at authorized retailers. Checked {upd:%b %-d}, plus the best dupes.",
 f"<h1>Today's best designer fragrance deals</h1><p class='sub'>{len(deals)} live deals on authentic bottles · last checked {upd_h} · sorted by % off</p>"
 +BREVO_FORM
 +f"<div class='grid'>{''.join(card(d,i<2) for i,d in enumerate(deals))}</div><p class='chips'><a href='{PREFIX}/gifts/'>Holiday fragrance gifts</a>"
 +"".join(f"<a href='{PREFIX}/gifts/{slug}/'>{e(label)}</a>" for slug,label in SEO_GIFTS)+"</p>{bestchips()}"
 +"<section class='box'><h2 style='margin-top:0'>Why trust these deals?</h2><p>We only list authorized or long-established retailers (no anonymous marketplace sellers), re-check every price and stock status daily, and drop expired deals automatically. Want the smell for less? See our <a href='"+PREFIX+"/dupes/'>dupes directory</a>.</p></section>",
 [itemlist(deals,"Today's designer fragrance deals"),{"@context":"https://schema.org","@type":"WebSite","name":NAME,"url":BASE+PREFIX+"/"}])
# confirmation page for the Brevo double opt-in email; not for search
top=deals[:4]
use_sid("sub")
page("subscribed/index.html",f"You're subscribed | {NAME}",
 "Thanks for confirming your ScentDealsDaily email. The Friday note lists fragrance discounts we checked.",
 f"""<h1>You're subscribed</h1>
<p>Thanks for confirming. Every Friday morning you'll get the week's biggest real fragrance discounts.</p>
<p class="sub">Add <a href="mailto:deals@scentdealsdaily.com">deals@scentdealsdaily.com</a> to your contacts so the Friday email doesn't land in spam.</p>
<p><a class="btn" href="{PREFIX}/" style="max-width:280px">Today's deals</a></p>
<h2>A few of today's deals</h2><div class="grid">{''.join(card(d) for d in top)}</div>""",
 index=False)
# dupes
use_sid("dupes")
rows="".join(f"""<tr><td><b>{e(d['original'])}</b>{('<div class=meta>'+e(d['original_price'])+'</div>') if d.get('original_price') else ''}</td>
<td><b><a href='{PREFIX}/dupe/{slug(d["original"]+" dupe "+d["dupe"])}/'>{e(d['dupe'])}</a></b><div class=meta>{e(d['notes'])}</div></td>
<td>{(f"<b>${d['price']:.2f}</b> ({e(d['size'])}) {ext_a(d['url'], e(d.get('retailer') or 'Retailer'), placement='table')}<div class=meta>checked {upd_h}</div>") if d['price'] else "<span class=meta>Not tracked yet — price check coming</span>"}</td>
<td class=meta>{' '.join((f'<a href="{e(affiliate_url(s, "src"))}" rel="nofollow sponsored noopener" target="_blank">[{i+1}]</a>' if is_perfumania(s) else f"<a href='{e(s)}' rel=noopener target=_blank>[{i+1}]</a>") for i,s in enumerate(d['sources']))}</td></tr>""" for d in D["dupes"])
faq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":f"What is the best dupe for {d['original']}?","acceptedAnswer":{"@type":"Answer","text":f"{d['dupe']} is a widely cited alternative to {d['original']} ({d['notes']})."+(f" It was ${d['price']:.2f} for {d['size']} at {d.get('retailer') or 'the retailer'} as of {upd:%Y-%m-%d}." if d['price'] else "")}} for d in D["dupes"]]}
page("dupes/index.html",fit([f"Best Designer Fragrance Dupes {upd.year}: {len(D['dupes'])} Clones With Live Prices | {NAME}",f"Best Fragrance Dupes {upd.year}: {len(D['dupes'])} Clones With Live Prices"]),
 "Creed Aventus, Baccarat Rouge 540, Angels' Share, Sauvage Elixir and more: the most-cited affordable dupes, with today's prices and sources.",
 f"<h1>Designer fragrance dupes directory</h1><p class='sub'>Popular designer → affordable alternative pairs, cited from fragrance community rankings. Dupes are legally sold originals \"inspired by\" a scent — not counterfeits.</p>"+(("<p class='chips'>Compare guides: "+"".join(f"<a href='{PREFIX}/dupes/{h['slug']}/'>{e(h['title'])}</a>" for h in HUBS)+"</p>") if HUBS else "")+f"<table><thead><tr><th>Designer original</th><th>Dupe</th><th>Today's price</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>{BREVO_FORM}",[faq])
# gender/category pages
for g,label in [("men","Men's Cologne"),("women","Women's Perfume"),("unisex","Unisex Fragrance")]:
    ds=[d for d in deals if d["gender"]==g]
    if not ds: continue
    use_sid(g)
    tb=", ".join(dict.fromkeys(d['brand'] for d in ds))
    tb=tb if len(tb)<50 else tb[:tb.rfind(",",0,50)]+" & more"
    mx=max(d['pct_off'] for d in ds)
    page(f"{g}/index.html",fit([f"{label} Deals Today ({upd:%b %-d}): Up to {mx}% Off | {NAME}",f"{label} Deals: Up to {mx}% Off Today | {NAME}",f"{label} Deals Today ({upd:%b %-d}): Up to {mx}% Off"]),
      f"{len(ds)} authentic {label.lower()} deals from ${min(d['price'] for d in ds):.2f}, up to {max(d['pct_off'] for d in ds)}% off at authorized retailers: {tb}. Checked {upd:%b %-d}.",
      f"<h1>{label} deals</h1><p class='sub'>{len(ds)} live · checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{BREVO_FORM}{bestchips()}",[itemlist(ds,label+" deals")])
brands=sorted({canon(d["brand"]) for d in deals})
for b in brands:
    ds=[d for d in deals if canon(d["brand"])==b]
    use_sid("brand", bslug(b))
    nm=", ".join(fullname(d).replace(b+" ","",1) for d in ds[:2])+(" & more" if len(ds)>2 else "")
    mx=max(d['pct_off'] for d in ds)
    page(f"brands/{bslug(b)}/index.html",fit([f"{b} Perfume & Cologne Deals: Up to {mx}% Off Today | {NAME}",f"{b} Perfume & Cologne Deals: Up to {mx}% Off | {NAME}",f"{b} Perfume & Cologne Deals: Up to {mx}% Off Today",f"{b} Perfume & Cologne Deals: Up to {mx}% Off",f"{b} Fragrance Deals: Up to {mx}% Off"]),
      f"{len(ds)} verified {b} fragrance deal{'s' if len(ds)>1 else ''} from ${min(d['price'] for d in ds):.2f} ({nm}). Authentic, price-checked {upd:%b %-d, %Y}.",
      f"<h1>{e(b)} deals</h1><p class='sub'>checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{BREVO_FORM}",[itemlist(ds,b+" deals")])
page("brands/index.html",fit([f"Fragrance Deals by Brand: {len(brands)} Designer Brands on Sale Today | {NAME}",f"Fragrance Deals by Brand: {len(brands)} Designer Brands on Sale Today"]),f"Browse today's verified perfume and cologne discounts from {len(brands)} brands including {', '.join(brands[:4])}. Authorized retailers only, checked daily.",
 "<h1>Deals by brand</h1><div class='chips'>"+"".join(f"<a href='{PREFIX}/brands/{bslug(b)}/'>{e(b)}</a>" for b in brands)+"</div>")
page("sponsor/index.html",f"Advertise on {NAME}: Featured Fragrance Deals","Reach shoppers ready to buy designer perfume and cologne: featured deal spots, Friday newsletter sponsorships and dupe spotlights, always labeled Sponsored.",
 f"""<h1>Feature your fragrance brand</h1><p class='sub'>Put your scent in front of shoppers who are ready to buy.</p>
<div class='box'><h2 style='margin-top:0'>Options</h2><ul><li><b>Featured deal</b> — pinned at the top of the homepage for 7 days, clearly labeled "Sponsored".</li>
<li><b>Newsletter sponsor</b> — one slot in the Friday deals email.</li><li><b>Dupe spotlight</b> — your house featured on the dupes directory (must be an original composition, not a counterfeit).</li></ul>
<p>Rules: authentic products only, every sponsored placement labeled, no fake reviews.</p>
<p>Contact: <a href="mailto:hello@scentdealsdaily.com">hello@scentdealsdaily.com</a> (pricing on request).</p></div>""")
page("disclosure/index.html",f"Affiliate Disclosure | {NAME}","How ScentDealsDaily earns money: retailer affiliate commissions at no extra cost to you and clearly labeled sponsored spots. Deals are always ranked by % off.",
 """<h1>Affiliate disclosure</h1><div class='box'><p>We may earn a commission when you buy through our links, at no extra cost to you.</p>
<p>Some links on this site are affiliate links, including links to Perfumania and FragranceShop. If you buy through them, we may earn a commission at no extra cost to you. This never changes which deals we list or how they're ranked (by % off). When the same sealed bottle is in stock at both stores, the buy button goes to the lower price we checked, and the other store is noted beside it.</p>
<p>As an Amazon Associate we may earn from qualifying purchases (once enrolled). Sponsored placements are always labeled "Sponsored".</p>
<p>"Was" prices are the retailer's own listed compare-at / retail price at the time we checked. Prices and stock change; always confirm at checkout.</p></div>""")
open(f"{OUT}/style.css","w").write(CSS)
if CUSTOM_DOMAIN: open(f"{OUT}/CNAME","w").write(CUSTOM_DOMAIN+"\n")
open(f"{OUT}/robots.txt","w").write(
    "User-agent: *\nAllow: /\n"
    "Disallow: /go/\nDisallow: /out/\nDisallow: /redirect/\nDisallow: /r/\n\n"
    f"Sitemap: {BASE}{PREFIX}/sitemap.xml\n")
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
use_sid("llms")
def plain_url(url):
    """Retailer or citation URL safe to publish where a bot will fetch every link."""
    return links.retailer_url(url) or url
llms=[f"# {NAME}",f"> Daily-checked discounts on authentic designer fragrances at reputable retailers, plus a cited dupes directory. Last updated {D['updated']}.","",
 "## Today's deals (price USD, size, retailer, % off listed compare-at)"]+[f"- {d['brand']} {d['name']} {d['size']}: ${d['price']:.2f} (was ${d['was']:.2f}, -{d['pct_off']}%) at {d['retailer']}: {plain_url(d['url'])}" for d in deals]+["","## Dupes (designer original -> alternative)"]+[f"- {d['original']} -> {d['dupe']}"+(f": ${d['price']:.2f} {d['size']} at {d['retailer']} {plain_url(d['url'])}" if d['price'] else "")+f" (sources: {', '.join(plain_url(s) for s in d['sources'])})" for d in D['dupes']]+["","## Pages",f"- Deals: {BASE}{PREFIX}/",f"- Dupes: {BASE}{PREFIX}/dupes/",f"- Raw data (JSON): {BASE}{PREFIX}/deals.json"]
open(f"{OUT}/llms.txt","w").write("\n".join(llms)+"\n")
json.dump(D,open(f"{OUT}/deals.json","w"))
open(f"{OUT}/.nojekyll","w").write("")
print(len(PAGES),"pages ->",OUT)

def comprows(d):
    cs=d.get('comps') or [{"retailer":d['retailer'],"price":d['price'],"url":d['url'],"checked":upd_h}]
    cs=sorted(cs,key=lambda c:c['price'])
    return "".join(f"<tr><td>{ext_a(c['url'], e(c['retailer']), placement='table')}{' <span class=badge>lowest</span>' if i==0 else ''}</td><td>{e(d.get('size') or '')}</td><td><b>${c['price']:.2f}</b></td><td class=meta>{e(c['checked'] if 'T' not in str(c['checked']) else upd_h)}</td></tr>" for i,c in enumerate(cs))
# ---------- SEO landing pages: one per fragrance deal + one per dupe pair ----------
import hashlib
def faqld(qs): return {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in qs]}
def faqhtml(qs): return "<section class='box'><h2 style='margin-top:0'>FAQ</h2>"+"".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q,a in qs)+"</section>"
def buy(url,ret): return ext_a(url, f"Buy at {e(ret)} →", cls="btn", style="max-width:340px", placement="cta")
KW=[]
for d in deals:
    full=fullname(d); s=slug(f"{d['brand']} {d['name']}"); use_sid("deal", s); KW+= [f"{full.lower()} cheapest price",f"{full.lower()} sale",f"{full.lower()} {d['size'].lower()} deal"]
    gl={"men":"men's cologne","women":"women's perfume","unisex":"unisex fragrance"}[d['gender']]
    others=[x for x in deals if x['gender']==d['gender'] and x['id']!=d['id']][:4]
    qs=[(f"What is the cheapest price for {full} right now?",f"As of {upd_h}, the lowest price we verified is ${d['price']:.2f} for {d['size']} at {d['retailer']}, {d['pct_off']}% below {('the $%.2f at %s' % (d['was'],d['was_label'])) if d.get('was_label') else ('its listed $%.2f' % d['was'])}."),
        (f"Is {full} on sale?",f"{d['retailer']} has it at ${d['price']:.2f} versus ${d['was']:.2f} {('at '+d['was_label']) if d.get('was_label') else 'listed compare-at'}. We re-check daily and remove it when the deal ends."),
        (f"Is the {d['retailer']} {full} authentic?",f"{d['retailer']} is a long-established US fragrance chain selling genuine designer brands. We exclude marketplace sellers and tester listings."),
        (f"How much does {full} cost per ounce?",(f"At ${d['price']:.2f} for {d['size']} it works out to ${per_oz(d):.2f} per ounce, and you save ${d['was']-d['price']:.2f} versus the ${d['was']:.2f} listed price." if per_oz(d) else f"At ${d['price']:.2f} you save ${d['was']-d['price']:.2f} versus the ${d['was']:.2f} listed price."))]
    rus=roundups_of(d)
    body=(f"<h1>{e(full)} {e(sz(d['size']))}: cheapest price today</h1><p class='sub'>Lowest verified price: <b class='price'>${d['price']:.2f}</b> <span class='was'>${d['was']:.2f}</span> <span class='badge'>-{d['pct_off']}%</span> at {e(d['retailer'])} · checked {upd_h}</p>"
      +buy(d['url'],d['retailer'])+also_line(d)
      +f"<div class='box' style='display:flex;gap:16px;flex-wrap:wrap'><img src='{e(d['image'] or '')}' alt='{e(full)}' width=220 height=220 fetchpriority=high decoding=async style='object-fit:contain'><div style='flex:1;min-width:220px'><h2 style='margin-top:0'>Price comparison</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table><p class=meta>More retailers are added as we verify them. We never list unverified prices.</p></div></div>"
      +BREVO_FORM
      +f"<p>{e(full)} is one of today's best {gl} deals: {d['pct_off']}% {('below the '+e(d['was_label'])+' price') if d.get('was_label') else 'off the listed price'}, a {d['type'].lower() or 'fragrance'} from {e(d['brand'])} (<a href='{PREFIX}/brands/{bslug(d['brand'])}/'>all {e(canon(d['brand']))} deals</a>{"".join(", <a href='"+PREFIX+"/best/"+ru['slug']+"/'>"+e(ru['title'].lower().replace('best ','more '))+"</a>" for ru in rus)}).</p>"
      +"".join(f"<p><b>Comparing?</b> <a href='{PREFIX}/vs/{v['slug']}/'>{e(v['title'])}: prices, size and notes side by side</a></p>" for v in vs_of(d))
      +faqhtml(qs)+"<h2>Similar deals today</h2><div class='grid'>"+"".join(card(x) for x in others)+"</div>")
    short=re.sub(r"( Spray)? (Cologne|Perfume|Unisex Fragrance)$","",full); P=f"${d['price']:.2f}"; Z=sz(d['size'])
    page(f"fragrance/{s}/index.html",fit([f"{full} {Z} Sale: {P} ({d['pct_off']}% Off) – Cheapest Price {upd:%b %Y}",f"{full} {Z} Sale: {P} ({d['pct_off']}% Off)",f"{short} {Z} Sale: {P} ({d['pct_off']}% Off)",f"{short} {Z}: {P} ({d['pct_off']}% Off)",f"{short}: {P} ({d['pct_off']}% Off)",f"{short.replace(canon(d['brand'])+' ','',1).replace(d['brand']+' ','',1)} {Z}: {P} ({d['pct_off']}% Off)"]),
      f"{full} {sz(d['size'])} for ${d['price']:.2f} at {d['retailer']} ("+(f"${d['was']:.2f} at {d['was_label']}" if d.get('was_label') else f"was ${d['was']:.2f}")+f"). Authentic, sealed, price-checked {upd:%b %-d, %Y}.",body,
      [prod_ld(d, name=f"{full} {d['size']}", brand=d['brand']),faqld(qs)])
def nohouse(n):
    """Name without the house prefix (Armaf/Lattafa/MFK/YSL...), for titles that would run past 60 chars."""
    w=re.sub(r' [(].*?[)]','',n).split(); k=2 if w[0] in ("Al","Ariana") else 1
    return " ".join(w[k:]) if len(w)>k else n
for d in D["dupes"]:
    s=slug(f"{d['original']} dupe {d['dupe']}"); use_sid("dupe", s); o=d['original']
    KW+=[f"{o.lower()} dupe",f"best cheap {o.lower()} dupe {upd.year}",f"{d['dupe'].lower()} vs {o.lower()}"]
    pr=f"${d['price']:.2f} for {d['size']} at {d['retailer']}" if d['price'] else "not yet price-verified by us"
    qs=[(f"What is the best cheap {o} dupe in {upd.year}?",f"{d['dupe']} is one of the most-cited affordable alternatives to {o}: {d['notes']}. Today: {pr}."),
        (f"Does {d['dupe']} smell like {o}?",f"Community rankings rate it as close ({d['notes']}). It is an original 'inspired by' fragrance, not a counterfeit; expect differences in the dry-down."),
        (f"Where can I buy {d['dupe']} cheapest?",f"The lowest price we verified is {pr}" + (f" (checked {upd_h})." if d['price'] else ". Check back; we add prices only after verifying them."))]
    rel=[x for x in D['dupes'] if x is not d][:5]
    hb=hub_of(d); hublink=(f"<a href='{PREFIX}/dupes/{hb['slug']}/'>Compare every {e(hb['topic'])} dupe side by side</a> · ") if hb else ""
    body=(f"<h1>Best {e(o)} dupe: {e(d['dupe'])}</h1><p class='sub'>{e(d['notes'])} · {('<b class=price>$%.2f</b> today at %s' % (d['price'],e(d['retailer']))) if d['price'] else 'price not verified yet'}</p>"
      +((buy(d['url'],d['retailer'])+also_line(d)) if d['price'] else "")
      +f"<div class='box'><h2 style='margin-top:0'>{e(o)} vs {e(d['dupe'])}</h2><table><thead><tr><th></th><th>{e(o)}</th><th>{e(d['dupe'])}</th></tr></thead><tbody><tr><td>Price</td><td>{e(d.get('original_price') or 'varies')}</td><td>{('$%.2f (%s)' % (d['price'],e(d['size']))) if d['price'] else '—'}</td></tr><tr><td>Profile</td><td colspan=2>{e(d['notes'])}</td></tr><tr><td>Sources</td><td colspan=2>{' '.join((f'<a href="{e(affiliate_url(x, "src"))}" rel="nofollow sponsored noopener" target="_blank">[{i+1}]</a>' if is_perfumania(x) else f'<a href={e(x)} rel=noopener target=_blank>[{i+1}]</a>') for i,x in enumerate(d['sources']))}</td></tr></tbody></table></div>"
      +((f"<div class='box'><h2 style='margin-top:0'>Where to buy {e(d['dupe'])} cheapest</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table></div>") if d.get('comps') else "")+faqhtml(qs)+"<h2>More dupes</h2><div class='chips'>"+"".join(f"<a href='{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/'>{e(x['original'])} → {e(x['dupe'])}</a>" for x in rel)+"</div><p>"+hublink+f"<a href='{PREFIX}/dupes/'>All dupes</a></p>")
    lds=[faqld(qs)]+([prod_ld(d, name=d['dupe'], brand=d['dupe'].split()[0])] if d['price'] else [])
    PR=(f" ${d['price']:.2f}" if d['price'] else "")
    bare=re.sub(r' [(].*?[)]','',o)
    page(f"dupe/{s}/index.html",fit([f"Best {o} Dupe {upd.year}: {d['dupe']}{PR}",f"Best {o} Dupe: {d['dupe']}{PR}",f"{o} Dupe: {d['dupe']}{PR}",f"{bare} Dupe: {nohouse(d['dupe'])}{PR}" if d['price'] else "",f"{nohouse(o)} Dupe: {nohouse(d['dupe'])}{PR}" if d['price'] else "",f"{o} Dupe: {d['dupe']}",f"{bare} Dupe: {re.sub(r' [(].*?[)]','',d['dupe'])}",f"{o} Dupe: {nohouse(d['dupe'])}",f"{nohouse(o)} Dupe: {nohouse(d['dupe'])}"]),
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
def offer_item(d, name, brand):
    x=prod_ld(d, name=name, brand=brand); x.pop("@context",None); return x
for r in ROUNDUPS:
    use_sid("best", r["slug"])
    ds=sorted(r["items"],key=lambda d:(per_oz(d) or 999,d['price'])); n=len(ds); N=r['noun']
    cheap=min(ds,key=lambda d:d['price']); val=ds[0]; big=max(ds,key=lambda d:d['pct_off'])
    SC=r['scope']; KW+=[r['title'].lower().replace('best ','best cheap ').replace(' deals',''),r['title'].lower(),f"designer {N} {SC}"]
    others=[x for x in ROUNDUPS if x is not r]
    NT=r.get('notes') or {}
    rows="".join(f"<tr><td><a href='{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/'>{e(fullname(d))}</a><div class=meta>{e(d['type'] or '')}{(' · '+e(NT[d['id']])) if d['id'] in NT else ''}</div></td><td>{e(d['size'])}</td><td><b>${d['price']:.2f}</b> <span class=was>${d['was']:.2f}</span></td><td>{('$%.2f' % per_oz(d)) if per_oz(d) else '—'}</td><td><span class=badge>-{d['pct_off']}%</span></td><td>{ext_a(d['url'], 'Buy at '+e(d['retailer']), placement='table')}</td></tr>" for d in ds)
    qs=[(f"What is the cheapest {N} deal {SC} today?",f"As of {upd_h}, the lowest verified price is {fullname(cheap)} {cheap['size']} at ${cheap['price']:.2f} from {cheap['retailer']} ({cheap['pct_off']}% off ${cheap['was']:.2f})."),
        (f"Which {N} {SC} is the best value per ounce?",f"{fullname(val)} at ${per_oz(val):.2f} per ounce (${val['price']:.2f} for {val['size']})." if per_oz(val) else f"{fullname(val)} at ${val['price']:.2f}."),
        (f"Which {N} {SC} has the biggest discount?",f"{fullname(big)}: {big['pct_off']}% off, ${big['price']:.2f} versus ${big['was']:.2f} {('at '+big['was_label']) if big.get('was_label') else 'listed compare-at'}."),
        (f"Are these {N} deals authentic?","Yes. We only list authorized, long-established retailers (Perfumania and FragranceShop, both US fragrance shops selling genuine designer brands) and exclude marketplace sellers, testers and unboxed bottles."),
        ("How often are these prices updated?",f"Every day. Each price, compare-at price and stock status is re-checked from the retailer's live product data; anything that drops below 15% off or sells out is removed automatically. Last check: {upd_h}.")]+[tuple(x) for x in r.get('faq',[])]
    body=(f"<h1>{e(r['title'])} ({upd:%b %-d, %Y})</h1><p class='sub'>{n} authentic {r['who']} fragrances {SC}, each at least 15% below its listed price · checked {upd_h}</p>"+(f"<p>{e(r['lead'])}</p>" if r.get('lead') else "")
      +"<div class='box'><h2 style='margin-top:0'>Quick picks</h2><ul>"+picks(cheap,val,big)+"</ul>"
      +"<p class='meta'>How we pick: "+e(r['rule'])+", at least 15% below the retailer's listed compare-at price (or another authorized retailer's price, where shown), in stock, and sold by an authorized retailer. Sorted by price per ounce so bigger bottles get credit for real value, not just a low sticker.</p></div>"
      +f"<table><thead><tr><th>Fragrance</th><th>Size</th><th>Price</th><th>Per oz</th><th>Off</th><th></th></tr></thead><tbody>{rows}</tbody></table>"
      +BREVO_FORM
      +f"<h2>All {n} picks</h2><div class='grid'>{''.join(card(d) for d in ds)}</div>"+faqhtml(qs)
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/best/{x['slug']}/'>{e(x['title'])}</a>" for x in others)+f"<a href='{PREFIX}/men/'>All men's deals</a><a href='{PREFIX}/women/'>All women's deals</a><a href='{PREFIX}/dupes/'>Designer dupes</a></p>")
    il={"@context":"https://schema.org","@type":"ItemList","name":r['title'],"numberOfItems":n,"itemListElement":[{"@type":"ListItem","position":i+1,"item":offer_item(d, f"{fullname(d)} {d['size']}", d['brand'])} for i,d in enumerate(ds)]}
    CP=f"${cheap['price']:.2f}"
    page(f"best/{r['slug']}/index.html",fit([f"{r['title']} Today ({upd:%b %-d}): {n} Authentic Picks | {NAME}",f"{r['title']} Today: {n} Picks From {CP}",f"{r['title']}: {n} Picks From {CP}",f"{r['title']} ({upd:%b %Y})"]),
      fit([f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off, from ${cheap['price']:.2f} ({fullname(cheap)}). Ranked by price per ounce, checked {upd:%b %-d, %Y}.",
           f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off, from {CP} ({fullname(cheap)}). Checked {upd:%b %-d}.",
           f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off at authorized retailers, from {CP}. Ranked by price per ounce, checked {upd:%b %-d}."],160),body,[il,faqld(qs)])
def house(name):
    w=name.split(); return " ".join(w[:2]) if w[0] in ("Al","Ariana") else w[0]
def srclinks(srcs): return " ".join((f'<a href="{e(affiliate_url(u, "src"))}" rel="nofollow sponsored noopener" target="_blank">[{i+1}]</a>' if is_perfumania(u) else f"<a href='{e(u)}' rel=noopener target=_blank>[{i+1}]</a>") for i,u in enumerate(srcs))
def hubrow(x):
    link=f"{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/"
    op=f"<div class=meta>{e(x['original_price'])}</div>" if x.get('original_price') else ""
    if x.get('price'):
        price=f"<b>${x['price']:.2f}</b> ({e(x['size'])}) "+ext_a(x['url'],e(x['retailer']), placement="table"); po=per_oz(x); pz=f"${po:.2f}" if po else "—"
    else: price="<span class=meta>not price-verified yet</span>"; pz="—"
    return f"<tr><td><b>{e(x['original'])}</b>{op}</td><td><b><a href='{link}'>{e(x['dupe'])}</a></b><div class=meta>{e(x['notes'])}</div></td><td>{price}</td><td>{pz}</td><td class=meta>{srclinks(x['sources'])}</td></tr>"
# ---------- dupe hubs (/dupes/<slug>/) ----------
for h in HUBS:
    use_sid("hub", h["slug"])
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
      +BREVO_FORM
      +"<p class='meta'>Profiles summarize the cited community clone lists; how close a dupe smells is subjective and dry-downs differ. Prices are shown only after we verify them live.</p>"
      +faqhtml(qs)+"<p class='chips'>"+"".join(f"<a href='{PREFIX}/dupes/{x['slug']}/'>{e(x['title'])}</a>" for x in HUBS if x is not h)+f"<a href='{PREFIX}/dupes/'>All dupes</a></p>")
    il={"@context":"https://schema.org","@type":"ItemList","name":h['title'],"numberOfItems":len(pr),"itemListElement":[{"@type":"ListItem","position":i+1,"item":offer_item(x, x['dupe'], x['dupe'].split()[0])} for i,x in enumerate(pr)]}
    FR=(f" From ${cheapest['price']:.2f}" if cheapest else "")
    page(f"dupes/{h['slug']}/index.html",fit([f"{h['title']} {upd.year}: {len(ms)} Clones Compared{FR} | {NAME}",f"{h['title']} {upd.year}: {len(ms)} Clones Compared{FR}",f"{h['title']} {upd.year}: {len(ms)} Clones{FR}",f"{h['title']} {upd.year}"]),
      fit([f"{', '.join(x['dupe'] for x in ms)} compared: scent profiles, cited sources and verified prices"+(f" from ${cheapest['price']:.2f}" if cheapest else "")+".",
           f"{len(ms)} {T} dupes from {houses} compared: scent profiles, cited sources and verified prices"+(f" from ${cheapest['price']:.2f}" if cheapest else "")+"."],160),body,([il] if pr else [])+[faqld(qs)])
# ---------- head-to-head comparisons (/vs/<slug>/) ----------
def conc(t):
    t=(t or "").lower()
    return "Parfum" if t.startswith("parfum") else "Eau de Parfum" if "parfum" in t else "Eau de Toilette" if "toilette" in t else (t.title() or "—")
for v in VS:
    use_sid("cmp", v["slug"])
    A,B=v['A'],v['B']; fa,fb=fullname(A),fullname(B); T=v['title']
    pa,pb=per_oz(A),per_oz(B)
    cheaper=min((A,B),key=lambda d:d['price']); value=min((A,B),key=lambda d:per_oz(d) or 999); bigger=max((A,B),key=lambda d:d['pct_off'])
    ca,cb=conc(A['type']),conc(B['type'])
    def cell(d): return f"<b>${d['price']:.2f}</b> <span class=was>${d['was']:.2f}</span> <span class=badge>-{d['pct_off']}%</span>"
    def bt(d): return ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn", placement="table")
    rows=(f"<tr><td>Price today</td><td>{cell(A)}</td><td>{cell(B)}</td></tr>"
      f"<tr><td>Size</td><td>{e(sz(A['size']))}</td><td>{e(sz(B['size']))}</td></tr>"
      f"<tr><td>Price per ounce</td><td>{('$%.2f' % pa) if pa else '—'}</td><td>{('$%.2f' % pb) if pb else '—'}</td></tr>"
      f"<tr><td>Concentration</td><td>{e(ca)}</td><td>{e(cb)}</td></tr>"
      f"<tr><td>Key notes</td><td>{e(v['a_notes'])}</td><td>{e(v['b_notes'])}</td></tr>"
      f"<tr><td>Cheapest at</td><td>{e(A['retailer'])}</td><td>{e(B['retailer'])}</td></tr>"
      f"<tr><td></td><td>{bt(A)}</td><td>{bt(B)}</td></tr>")
    same_conc=ca==cb
    RANK={"Eau de Toilette":1,"Eau de Parfum":2,"Parfum":3}
    def an(x): return ("an " if x[:1].upper() in "AEIOU" else "a ")+x
    hi,lo=((A,ca),(B,cb)) if RANK.get(ca,0)>=RANK.get(cb,0) else ((B,cb),(A,ca))
    qs=[(f"Which is cheaper, {fa} or {fb}?",f"As of {upd_h}, {fullname(cheaper)} is the lower price at ${cheaper['price']:.2f} for {sz(cheaper['size'])} ({cheaper['retailer']})."+(f" Per ounce, {fullname(value)} is the better value at ${per_oz(value):.2f}/oz." if per_oz(value) else "")),
        (f"What is the difference between {fa} and {fb}?",v['difference']),
        (f"Is {fa} or {fb} stronger?",(f"Both are sold as {ca}, so concentration alone doesn't separate them; performance depends on the composition and your skin." if same_conc else f"{fa} is {an(ca)} and {fb} is {an(cb)}. {hi[1]} has a higher concentration of fragrance oils than {lo[1].lower()}, so {fullname(hi[0])} usually lasts longer and projects more, though skin chemistry matters.")),
        ("Are these bottles authentic?","Yes. We only link to authorized, long-established fragrance retailers (Perfumania and FragranceShop) and exclude marketplace sellers, testers and unboxed bottles. Prices are re-checked daily.")]
    KW+=[T.lower(),f"{T.lower()} which is better",f"{fa.lower()} or {fb.lower()}"]
    body=(f"<h1>{e(T)}: price, size and notes compared</h1><p class='sub'>Both on sale today · checked {upd_h}</p><p>{e(v['intro'])}</p>"
      +f"<div class='box'><h2 style='margin-top:0'>Side by side</h2><table><thead><tr><th></th><th><a href='{PREFIX}/fragrance/{slug(A['brand']+' '+A['name'])}/'>{e(fa)}</a></th><th><a href='{PREFIX}/fragrance/{slug(B['brand']+' '+B['name'])}/'>{e(fb)}</a></th></tr></thead><tbody>{rows}</tbody></table>"
      +"<p class='meta'>Prices come from each retailer's live product data. Key notes summarize the brand's published notes; how a scent wears is personal.</p></div>"
      +BREVO_FORM
      +f"<div class='box'><h2 style='margin-top:0'>Which should you buy?</h2><ul><li><b>Lower price today:</b> {e(fullname(cheaper))} at ${cheaper['price']:.2f}.</li>"
      +(f"<li><b>Better value per ounce:</b> {e(fullname(value))} at ${per_oz(value):.2f}/oz.</li>" if per_oz(value) else "")
      +f"<li><b>Bigger discount:</b> {e(fullname(bigger))}, {bigger['pct_off']}% off.</li><li>{e(v['pick'])}</li></ul></div>"
      +faqhtml(qs)+"<h2>Both deals</h2><div class='grid'>"+card(A)+card(B)+"</div>"
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/best/{x['slug']}/'>{e(x['title'])}</a>" for x in ROUNDUPS if A in x['items'] or B in x['items'])+"".join(f"<a href='{PREFIX}/vs/{x['slug']}/'>{e(x['title'])}</a>" for x in VS if x is not v)+f"<a href='{PREFIX}/{A['gender']}/'>All {A['gender']}'s deals</a><a href='{PREFIX}/brands/{bslug(A['brand'])}/'>All {e(canon(A['brand']))} deals</a></p>")
    CP=f"${cheaper['price']:.2f}"
    page(f"vs/{v['slug']}/index.html",fit([f"{T}: Which to Buy? Prices From {CP} ({upd:%b %Y}) | {NAME}",f"{T}: Which to Buy? From {CP}",f"{T}: Which Is Better? From {CP}",f"{T} Compared: From {CP}",f"{T}: From {CP}",f"{T}: Which to Buy?",f"{T} Compared"]),
      fit([f"{fa} (${A['price']:.2f}, {sz(A['size'])}) vs {fb} (${B['price']:.2f}, {sz(B['size'])}): price per ounce, concentration and key notes compared. Checked {upd:%b %-d, %Y}.",
           f"{T}: ${A['price']:.2f} ({sz(A['size'])}) vs ${B['price']:.2f} ({sz(B['size'])}) today. Price per ounce, concentration, key notes and which to buy. Checked {upd:%b %-d}.",
           f"{T}: ${A['price']:.2f} ({sz(A['size'])}) vs ${B['price']:.2f} ({sz(B['size'])}) today. Price per ounce, key notes and which to buy."],160),body,
      [prod_ld(A, name=f"{fa} {sz(A['size'])}", brand=canon(A['brand'])),prod_ld(B, name=f"{fb} {sz(B['size'])}", brand=canon(B['brand'])),faqld(qs)])
# ---------- holiday gift guides (/gifts/...) ----------
def gift_blob(d):
    return " ".join(str(d.get(k) or "") for k in ("name","brand","type","size","retailer","url")).lower()
def gift_ok(d):
    """A checked bottle we can recommend. Testers, decants, and Amazon stay out."""
    if d.get("in_stock") is False: return False
    if isinstance(d.get("price"), bool) or not isinstance(d.get("price"), (int, float)): return False
    if not d.get("url") or not d.get("retailer"): return False
    blob=gift_blob(d)
    if re.search(r"\b(tester|testers|decant|decants)\b", blob): return False
    host=(urllib.parse.urlparse(d.get("url") or "").hostname or "").lower()
    if "amazon" in blob or "amazon." in host or host.endswith("amazon.com"): return False
    return True
def is_gift_set(d):
    blob=gift_blob(d)
    return any(s in blob for s in ("gift set","gift-set","coffret","discovery set"))
def is_mini_or_travel(d):
    """A mini or travel spray we actually checked. A 1 oz bottle is not one."""
    blob=gift_blob(d)
    if re.search(r"\b(mini|minis|miniature|travel|travel-size|travelsize|rollerball|roller-ball)\b", blob): return True
    o=oz(d.get("size") or "")
    return o is not None and o<1
def gift_line(d):
    """One plain line from concentration, size, and who it is for. No scent claims."""
    who={"men":"for men","women":"for women","unisex":"for men and women"}.get(d.get("gender"),"")
    bits=[b for b in (conc_name(d.get("type")), sz(d.get("size") or ""), who) if b]
    return ", ".join(bits)+"." if bits else "Price checked at an authorized retailer."
def gift_table(ds):
    rows=[]
    for d in ds:
        href=f"{PREFIX}/fragrance/{slug(d['brand']+' '+d['name'])}/"
        was=f" <span class=was>${d['was']:.2f}</span>" if isinstance(d.get("was"), (int, float)) and not isinstance(d.get("was"), bool) else ""
        label=(f"<div class=meta>compare-at price at {e(d['was_label'])}</div>" if d.get("was_label") else "")
        rows.append(f"<tr><td><a href='{href}'>{e(fullname(d))}</a><div class=meta>{e(gift_line(d))}</div>{label}</td><td><b>${d['price']:.2f}</b>{was}</td><td>{ext_a(d['url'], 'Buy at '+e(d['retailer']), placement='list')}</td></tr>")
    return "<table><thead><tr><th>Fragrance</th><th>Price</th><th></th></tr></thead><tbody>"+"".join(rows)+"</tbody></table>"
GIFT_LINKS=[("","Holiday gifts"),("for-him","For him"),("for-her","For her"),("under-50","Under $50"),("gift-sets","Gift sets")]+SEO_GIFTS
def gift_nav():
    return "<p class='chips'>"+"".join(f"<a href='{PREFIX}/gifts/{slug+'/' if slug else ''}'>{e(label)}</a>" for slug,label in GIFT_LINKS)+"</p>"
GIFT_DISC="<p>Affiliate disclosure: some links on this page earn us a commission if you buy, at no extra cost to you. Prices are the ones we checked at authorized retailers.</p>"
eligible=[d for d in deals if gift_ok(d)]
by_off=sorted(eligible, key=lambda d:(-(d.get("pct_off") or 0), d["price"], d["id"]))
gift_pages=[
 ("gifts/index.html","","Holiday fragrance gifts","Fragrance gifts from checked deals",
  "Single bottles on sale now, for November and December. Largest checked discount first.",
  by_off[:12],"Holiday fragrance gifts","/media/pins/holiday-fragrance-gifts.png"),
 ("gifts/for-him/index.html","for-him","Fragrance gifts for him","Men's cologne gifts",
  "Men's colognes from today's checked deals, largest discount first.",
  [d for d in by_off if d["gender"]=="men"][:12],"Fragrance gifts for him","/media/pins/cologne-gifts-for-him.png"),
 ("gifts/for-her/index.html","for-her","Fragrance gifts for her","Women's perfume gifts",
  "Women's perfumes from today's checked deals, largest discount first.",
  [d for d in by_off if d["gender"]=="women"][:12],"Fragrance gifts for her","/media/pins/perfume-gifts-for-her.png"),
 ("gifts/under-50/index.html","under-50","Fragrance gifts under $50","Gifts under $50",
  "The lowest prices we checked that are still under $50.",
  sorted([d for d in eligible if d["price"]<50], key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))[:12],"Fragrance gifts under $50","/media/pins/fragrance-gifts-under-50.png"),
 ("gifts/gift-sets/index.html","gift-sets","Fragrance gift sets","Checked fragrance gift sets",
  "Boxed sets only. A deal is listed here when the product we checked is a gift set.",
  [d for d in by_off if is_gift_set(d)][:12],"Fragrance gift sets","/media/pins/fragrance-gift-sets.png"),
]
for path,sid_slug,title,short,intro,picks,list_name,image in gift_pages:
    use_sid("gifts", sid_slug)
    if picks:
        lo=min(picks, key=lambda d:d["price"])
        hi=max(d.get("pct_off") or 0 for d in picks)
        P=f"${lo['price']:.2f}"
        desc=f"{len(picks)} {title.lower()} from {P} ({fullname(lo)}), up to {hi}% off at authorized retailers. Checked {upd:%b %-d, %Y}."
        listing=gift_table(picks)+BREVO_FORM
        ld=[itemlist(picks, list_name)]
        titles=fit([f"{title}: From {P} ({upd:%b %Y}) | {NAME}", f"{title}: From {P} | {NAME}", f"{title}: From {P}", title])
    else:
        desc="No boxed fragrance gift set is in today's checked deals. Single bottles on the other gift guides are the option until a set is in stock."
        listing="<p>None of the deals we checked today are boxed gift sets, so this page has no prices to show. Single bottles that work as gifts are on the other guides.</p>"
        ld=None
        titles=fit([f"{title} ({upd:%b %Y}) | {NAME}", f"{title} | {NAME}", title])
    page(path, titles,
      desc,
      f"<h1>{e(title)}</h1><p class='sub'>{e(intro)} Checked {upd_h}.</p>{gift_nav()}{GIFT_DISC}{listing}<p class='meta'>Each name links to that bottle's price comparison. We do not list testers, decants, or Amazon.</p>",
      ld, image=image)
    KW+=[title.lower(), f"fragrance {short.lower()}"]
def by_price(rows):
    return sorted(rows, key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))
def lowest_deal(rows):
    return min(rows, key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))
def seo_title(h1, picks):
    base=f"{h1}: From ${lowest_deal(picks)['price']:.2f}" if picks else h1
    named=f"{base} | {NAME}"
    return named if len(named)<=60 else base
def seo_meta_filled(n_label, picks):
    lo=lowest_deal(picks)
    price=f"${lo['price']:.2f}"
    when=f"{upd:%b %-d, %Y}"
    full=f"{len(picks)} {n_label}, starting at {price} for {fullname(lo)} ({sz(lo['size'])}) at {lo['retailer']}. Checked {when}. Sealed bottles only."
    if len(full)<=160: return full
    shorter=f"{len(picks)} {n_label}, starting at {price} for {fullname(lo)} ({sz(lo['size'])}) at {lo['retailer']}. Checked {when}."
    if len(shorter)<=160: return shorter
    return f"{len(picks)} {n_label}, starting at {price} at {lo['retailer']}. Checked {when}."
def render_seo_gift(slug_s, h1, intro, picks, faqs, empty_html, empty_desc, filled_label):
    use_sid("gifts", slug_s)
    title=seo_title(h1, picks)
    desc=seo_meta_filled(filled_label, picks) if picks else empty_desc
    listing=gift_table(picks) if picks else empty_html
    ld=([itemlist(picks, h1)] if picks else [])+[faqld(faqs)]
    page(f"gifts/{slug_s}/index.html", title, desc,
      f"<h1>{e(h1)}</h1><p class='sub'>{e(intro)} Checked {upd_h}.</p>{gift_nav()}{GIFT_DISC}{listing}{faqhtml(faqs)}{BREVO_FORM}<p class='meta'>Prices are copied from the deals we checked. We do not invent a price, and we do not list testers, decants, or Amazon.</p>",
      ld)
    KW.append(h1.lower())
her_under_50=by_price([d for d in eligible if d["gender"]=="women" and d["price"]<50])
men_under_40=by_price([d for d in eligible if d["gender"]=="men" and d["price"]<40])
mini_picks=by_price([d for d in eligible if is_mini_or_travel(d)])
set_picks=by_price([d for d in eligible if is_gift_set(d)])
her_lo=lowest_deal(her_under_50) if her_under_50 else None
men_lo=lowest_deal(men_under_40) if men_under_40 else None
render_seo_gift("perfume-gifts-for-her-under-50","Perfume gifts for her under $50",
  (f"{len(her_under_50)} women's perfumes from the deals we checked are under $50. Lowest price first." if her_under_50
   else "A perfume is listed here only when we checked a women's bottle under $50."),
  her_under_50,([
    ("What perfume gifts for her are under $50?",
     f"The lowest price we checked is ${her_lo['price']:.2f} for {fullname(her_lo)} ({sz(her_lo['size'])}) at {her_lo['retailer']}. {len(her_under_50)} women's perfumes on this page are under $50."),
    ("Are these prices estimated?",
     f"No. Each price is the price we checked at that row's retailer. Checked {upd_h}."),
    ("Do you include testers?",
     "No. These are sealed bottles at Perfumania or FragranceShop. Testers, decants, and Amazon are left out."),
  ] if her_under_50 else [
    ("Are there perfume gifts for her under $50 today?",
     "Not in the deals we checked. No women's perfume we priced today is under $50."),
    ("Will you estimate a price?",
     "No. A bottle is listed only after we check its price."),
    ("Where else can I look?",
     "The other gift guides list bottles we did check, including ones at $50 and above."),
  ]),
  "<p>None of the women's perfumes we checked today are under $50, so this page has no prices to show.</p>",
  "Perfume gifts for her under $50: none of today's checked women's perfumes is under $50. Other gift guides list bottles we did price.",
  "women's perfumes under $50")
render_seo_gift("best-mens-cologne-under-40","Best men's cologne under $40",
  (f"{len(men_under_40)} men's colognes from the deals we checked are under $40. Lowest price first. Unisex bottles are not listed here." if men_under_40
   else "A cologne is listed here only when we checked a men's bottle under $40. Unisex bottles are not listed here."),
  men_under_40,([
    ("What is the lowest men's cologne under $40 you checked?",
     f"{fullname(men_lo)} is ${men_lo['price']:.2f} for {sz(men_lo['size'])} at {men_lo['retailer']}. {len(men_under_40)} men's colognes on this page are under $40."),
    ("Why are some colognes missing?",
     "A bottle is listed only when today's checked price is under $40 and the product is a men's cologne. Unisex bottles stay off this page."),
    ("Are these prices estimated?",
     f"No. The prices were checked {upd_h} at authorized retailers. The store can change a price before you buy."),
  ] if men_under_40 else [
    ("Is there a men's cologne under $40 today?",
     "Not in the deals we checked. No men's cologne we priced today is under $40."),
    ("Are unisex bottles included?",
     "No. This page is men's cologne only."),
    ("Will you estimate a price?",
     "No. A bottle is listed only after we check its price."),
  ]),
  "<p>None of the men's colognes we checked today are under $40, so this page has no prices to show.</p>",
  "Best men's cologne under $40: none of today's checked men's colognes is under $40. Unisex bottles are not listed here.",
  "men's colognes under $40")
render_seo_gift("stocking-stuffer-minis","Stocking stuffer fragrance minis & travel sizes",
  "A mini or a travel spray is listed only when that is the product we priced. A 1 oz bottle is a small bottle, not a mini, so it stays on the other guides.",
  mini_picks,([
    ("What mini should I buy?",
     f"The lowest mini or travel size we checked is ${lowest_deal(mini_picks)['price']:.2f} for {fullname(lowest_deal(mini_picks))} ({sz(lowest_deal(mini_picks)['size'])}) at {lowest_deal(mini_picks)['retailer']}."),
    ("Is a 1 oz bottle a travel size?",
     "Not on this page. Travel sizes here are bottles under 1 oz, or products named mini or travel."),
    ("Are these prices estimated?",
     f"No. Checked {upd_h} at authorized retailers."),
  ] if mini_picks else [
    ("Are there fragrance minis or travel sizes today?",
     "Not in the deals we checked. Nothing today is named a mini or a travel spray, and nothing is a bottle under 1 oz."),
    ("Is a 1 oz bottle a mini?",
     "No. We leave 1 oz bottles on the perfume and cologne gift guides. This page is only for minis and travel sizes."),
    ("Where should I look instead?",
     "Perfume gifts for her under $50 and men's cologne under $40 list single bottles we did price."),
  ]),
  "<p>None of the deals we checked today are fragrance minis or travel sizes, so this page has no prices to show. Single bottles that work as gifts are on the other guides.</p>",
  "Stocking stuffer fragrance minis and travel sizes: none of today's checked deals is a mini or a travel spray. Bottles of 1 oz and up stay on the other guides.",
  "fragrance minis and travel sizes")
render_seo_gift("holiday-gift-sets","Fragrance gift sets for the holidays",
  "A holiday set is listed only when the product we checked is a boxed set, coffret, or discovery set. A single bottle is not listed as a set.",
  set_picks,([
    ("Which fragrance gift set is the lowest price?",
     f"The lowest set we checked is ${lowest_deal(set_picks)['price']:.2f} for {fullname(lowest_deal(set_picks))} at {lowest_deal(set_picks)['retailer']}."),
    ("Do you guess a set price?",
     f"No. A set is listed only after we check its price. Checked {upd_h}."),
    ("Are single bottles included?",
     "No. Single bottles stay on the other gift guides."),
  ] if set_picks else [
    ("Do you have fragrance gift sets for the holidays?",
     "Not today. None of the deals we checked is a gift set, coffret, or discovery set."),
    ("Will you guess a set price?",
     "No. A set is listed only after we check its price and that it is in stock."),
    ("What can I give instead?",
     "A single bottle from the other gift guides. Those prices are the ones we checked."),
  ]),
  "<p>None of the deals we checked today are boxed fragrance gift sets, so this page has no prices to show. Single bottles that work as gifts are on the other guides.</p>",
  "Fragrance gift sets for the holidays: none of today's checked deals is a boxed set, coffret, or discovery set. Single bottles are on the other gift guides.",
  "fragrance gift sets")
# rewrite sitemap with new pages + keyword list + IndexNow key
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
def rfc822(dt):
    days=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]; mons=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{days[dt.weekday()]}, {dt.day:02d} {mons[dt.month-1]} {dt.year} {dt:%H:%M:%S} +0000"
def write_feed():
    """RSS 2.0 for the latest deal and comparison pages. Descriptions are the pages' meta descriptions."""
    import xml.etree.ElementTree as ET
    groups={"deal":[],"compare":[],"hub":[],"dupe":[]}
    for kind,title,url,desc in FEED: groups[kind].append((title,url,desc))
    # Every roundup and vs page, then dupe hubs, then the steepest deals.
    # A fixed cap used to drop the newest guides once the compare list grew past it.
    items=groups["compare"]+groups["hub"]+groups["deal"][:8]
    ET.register_namespace("atom","http://www.w3.org/2005/Atom")
    rss=ET.Element("rss",{"version":"2.0"})
    ch=ET.SubElement(rss,"channel")
    def add(parent,tag,text,**attrs):
        el=ET.SubElement(parent,tag,attrs) if attrs else ET.SubElement(parent,tag)
        el.text=text
        return el
    add(ch,"title",NAME)
    add(ch,"link",f"{BASE}{PREFIX}/")
    add(ch,"description","Daily-checked deals and comparisons for authentic designer perfume and cologne.")
    add(ch,"language","en-us")
    add(ch,"lastBuildDate",rfc822(upd))
    ET.SubElement(ch,"{http://www.w3.org/2005/Atom}link",{"href":FEED_HREF,"rel":"self","type":"application/rss+xml"})
    published=rfc822(upd)
    for title,url,desc in items:
        it=ET.SubElement(ch,"item")
        add(it,"title",title)
        add(it,"link",url)
        add(it,"guid",url,isPermaLink="true")
        add(it,"pubDate",published)
        add(it,"description",desc)
    ET.indent(rss,space="  ")
    xml=ET.tostring(rss,encoding="unicode")
    open(f"{OUT}/feed.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n'+xml)
    return len(items)
nfeed=write_feed()
KEY=hashlib.md5(b"scentdealsdaily-indexnow").hexdigest(); open(f"{OUT}/{KEY}.txt","w").write(KEY)
open(f"{ROOT}/docs/keywords.txt","w").write("\n".join(KW)+"\n")
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Per-product & per-dupe pages\n"+"\n".join(u for u in PAGES if "/fragrance/" in u or "/dupe/" in u)+"\n")
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Buying guides & dupe comparisons\n"+"\n".join(u for u in PAGES if "/best/" in u or "/vs/" in u or "/gifts/" in u or any(f"/dupes/{h['slug']}/" in u for h in HUBS))+"\n")
print(len(PAGES),"pages total;",len(KW),"keywords;",nfeed,"feed items")
if _media_tmp:
    shutil.copytree(f"{_media_tmp}/media", f"{OUT}/media")
    shutil.rmtree(_media_tmp)
    print("copied site/media ->", OUT)

def audit_affiliate_output():
    """String-check every tracking href. Do not request tracking or /go links."""
    bad=[]
    tracking_hrefs=0
    href_re=re.compile(r"""href\s*=\s*(?:"([^"]+)"|'([^']+)')""", re.I)
    rel_re=re.compile(r"""rel\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
    for dirpath, _, files in os.walk(OUT):
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in (".html",".txt",".xml",".json",".css"): continue
            path=os.path.join(dirpath, fn)
            text=open(path, encoding="utf-8", errors="replace").read()
            relpath=os.path.relpath(path, OUT)
            for tag in re.findall(r"<a\b[^>]*>", text, re.I):
                hm=href_re.search(tag)
                href=html.unescape((hm.group(1) or hm.group(2)) if hm else "")
                if not (links.is_tracking_url(href) or links.is_internal_redirect(href)): continue
                tracking_hrefs+=1
                relm=rel_re.search(tag)
                relv=(relm.group(1) or relm.group(2) or "") if relm else ""
                tokens=set(relv.split())
                if not {"nofollow","sponsored","noopener"}<=tokens:
                    bad.append(f"{relpath}: affiliate link missing rel nofollow sponsored noopener")
                if tokens & {"prefetch","prerender"} or re.search(r"prefetch|prerender", tag, re.I):
                    bad.append(f"{relpath}: prefetch or prerender on an affiliate link")
                if links.is_tracking_url(href) and not links.affiliate_link_ok(href):
                    bad.append(f"{relpath}: affiliate link failed string check")
            stripped=re.sub(r"<a\b[^>]*>.*?</a>", " ", text, flags=re.I|re.S)
            low=stripped.lower()
            for domain in links.TRACKING_DOMAINS:
                if domain in low:
                    bad.append(f"{relpath}: {domain} outside an affiliate anchor")
                    break
            if re.search(r"""(?:href|url)\s*[=:]\s*["'][^"']*(?:/go/|/out/|/redirect/|/r/)""", stripped, re.I):
                bad.append(f"{relpath}: internal redirect URL outside an anchor")
    if re.search(r"""rel\s*=\s*["'][^"']*(?:prefetch|prerender)""", open(f"{OUT}/index.html", encoding="utf-8").read(), re.I):
        bad.append("homepage has prefetch or prerender")
    robots=open(f"{OUT}/robots.txt", encoding="utf-8").read()
    for rule in ("Disallow: /go/","Disallow: /out/","Disallow: /redirect/","Disallow: /r/"):
        if rule not in robots: bad.append(f"robots.txt missing {rule}")
    if open(f"{OUT}/CNAME", encoding="utf-8").read().strip()!=CUSTOM_DOMAIN:
        bad.append("CNAME changed")
    home=open(f"{OUT}/index.html", encoding="utf-8").read()
    for token in ("GASeKy1uEWpsrSn1II701znBYlw6mBhAwvimW0Yi8Io","AnNdRzKxRNra8nkj3gri7zC9kJYJ-aZehksWkrfImx4"):
        if token not in home: bad.append("missing Google site-verification meta tag")
    if bad:
        raise SystemExit("affiliate audit failed:\n"+"\n".join(bad[:40]))
    print(f"affiliate audit: {tracking_hrefs} tracking hrefs checked by string only; no prefetch; robots disallow redirect paths")
audit_affiliate_output()
