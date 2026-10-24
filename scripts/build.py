#!/usr/bin/env python3
"""Render data/deals.json -> static site in site/. Usage: SITE_URL=https://... python3 scripts/build.py

Also writes site/404.html (branded, noindex). That file is not added to sitemap.xml,
llms.txt, the feed, or IndexNow, which submits the sitemap.
Every page except the homepage and 404 gets a visible breadcrumb trail and one
BreadcrumbList JSON-LD block. A parent crumb is emitted only when that hub page
was built (for example /gifts/); a section with no hub is skipped.
"""
import json, os, html, re, datetime, urllib.parse, shutil, tempfile
import links
try:
    import pins as giftpins
except ImportError as _pin_err:
    raise SystemExit("gift pin images need Pillow. Install it with: python3 -m pip install pillow") from _pin_err
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
BRAND_CANON={"Lancome":"Lancôme","Mont Blanc":"Montblanc","Hermes":"Hermès"}  # retailer spellings -> the brand's own; one brand page
def canon(b): return BRAND_CANON.get(b,b)
def bslug(b): return slug(unicodedata.normalize("NFKD",canon(b)).encode("ascii","ignore").decode())
def sz(size): return re.sub(r"\s+"," ",size or "").strip().rstrip(".")
def _fullname(d):
    """Display name without a doubled brand ("Azzaro Azzaro Cologne" -> "Azzaro Cologne"). URLs keep brand+name slugs."""
    b,n=d['brand'],d['name']; cb=canon(b)
    if n.lower().startswith(b.lower()+" "): return cb+n[len(b):]
    if n.lower().startswith(cb.lower()+" "): return n
    last=cb.split()[-1]
    if " " in cb and n.lower().startswith(last.lower()+" "): return cb+n[len(last):]  # Hugo Boss + "Boss Bottled ..." -> "Hugo Boss Bottled ..."
    def fold(s):
        return re.sub(r"[^a-z0-9]+"," ", s.lower().replace("&"," and ")).strip()
    folded, brand_folded=fold(n), fold(cb)
    words=[w for w in brand_folded.split() if w!="and"]
    if folded==brand_folded or folded.startswith(brand_folded+" ") or (words and all(re.search(r"\b"+re.escape(w)+r"\b", folded) for w in words)):
        return n
    return f"{cb} {n}"
def fullname(d):
    """Display name; drops a stray "Spray" before Cologne/Perfume ("Defy Spray Cologne" -> "Defy Cologne")."""
    return re.sub(r" Spray (Cologne|Perfume)$",r" \1",_fullname(d))
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
.crumbs{font-size:13px;color:#6f6976;margin:0 0 8px}.crumbs a{text-decoration:none}.crumbs a:hover{text-decoration:underline}.crumbs .sep{margin:0 .35em;color:#b5aeb8}.crumbs [aria-current=page]{color:#5f5a66}
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
# Sitewide share image. Same 1000x1500 navy/gold pin format as site/media/pins/.
DEFAULT_SHARE="/media/og-default.png"
_PIN_INDEX=None
def pin_index():
    """Pin stems preserved in the media copy. site/ is wiped before pages render."""
    global _PIN_INDEX
    if _PIN_INDEX is not None: return _PIN_INDEX
    found={}
    root=f"{_media_tmp}/media/pins" if _media_tmp else ""
    if root and os.path.isdir(root):
        for fn in os.listdir(root):
            if fn.lower().endswith(".png"):
                found[os.path.splitext(fn)[0]]=f"/media/pins/{fn}"
    _PIN_INDEX=found
    return found
def page_slug(path):
    rel=path
    if rel.endswith("/index.html"): rel=rel[:-len("/index.html")]
    elif rel.endswith("index.html"): rel=rel[:-len("index.html")]
    rel=rel.strip("/")
    return rel.split("/")[-1] if rel else ""
def pin_for_page(path):
    """Existing /media/pins/ image whose name matches this page, or None."""
    pins=pin_index()
    slug=page_slug(path)
    if not slug: return None
    if slug in pins: return pins[slug]
    # A more specific page keeps the pin it extends (perfume-gifts-for-her-under-50).
    prefix=[stem for stem in pins if slug.startswith(stem+"-")]
    if prefix: return pins[max(prefix, key=len)]
    if not path.startswith("gifts/"): return None
    contained=[stem for stem in pins if len(stem)>=12 and stem in slug]
    # cologne-gifts-for-dad / boyfriend share the "for him" pin; mom / girlfriend share "for her".
    if slug.startswith("cologne-gifts-for-") and "cologne-gifts-for-him" in pins:
        contained.append("cologne-gifts-for-him")
    if "perfume-gifts-for-" in slug and "perfume-gifts-for-her" in pins:
        contained.append("perfume-gifts-for-her")
    if "gift-set" in slug:
        contained.extend(stem for stem in pins if "gift-set" in stem)
    if not contained: return None
    return pins[max(set(contained), key=len)]
def share_image(path, image):
    """Absolute og:image. Caller's image, else a matching pin, else the site default."""
    chosen=image or pin_for_page(path) or DEFAULT_SHARE
    if chosen.startswith(("http://","https://")): return chosen
    if not chosen.startswith("/"): chosen="/"+chosen
    return f"{BASE}{PREFIX}{chosen}"
def page(path,title,desc,body,jsonld=None,index=True,image=None,feed=True):
    if title in TITLES: title=f"{title} ({path.split('/')[0].title()})"
    TITLES.add(title); desc=clip(desc)
    url=f"{BASE}{PREFIX}/{path}".replace("/index.html","/")
    ld="".join(f'<script type="application/ld+json">{json.dumps(j,ensure_ascii=False)}</script>' for j in (jsonld or []))
    p=PREFIX
    has_form='id="sib-form"' in body
    brevo_head=BREVO_HEAD if has_form else ""
    brevo_js=BREVO_JS if has_form else ""
    robots="" if index else '<meta name="robots" content="noindex">'
    img=share_image(path, image)
    social=(f'<meta property="og:type" content="website"><meta property="og:site_name" content="{e(NAME)}">'
             f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
             f'<meta property="og:url" content="{url}">'
             f'<meta property="og:image" content="{e(img)}"><meta property="og:image:width" content="1000"><meta property="og:image:height" content="1500">'
             f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}">'
             f'<meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{e(img)}">')
    doc=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="GASeKy1uEWpsrSn1II701znBYlw6mBhAwvimW0Yi8Io" />
<meta name="google-site-verification" content="AnNdRzKxRNra8nkj3gri7zC9kJYJ-aZehksWkrfImx4" />
<meta name='impact-site-verification' value='6f939439-73de-427f-89fc-c18dc2f9f64d'>
<meta name="p:domain_verify" content="7833fa67293af531c9de288142c68c3c"/>
{robots}<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="ScentDealsDaily" href="{FEED_HREF}">
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
    if feed and k: FEED.append((k,title,url,desc))
PAGES=[]
FEED=[]  # (kind, title, url, plain meta description) for deal and comparison pages
def feed_kind(path):
    if path.startswith("fragrance/"): return "deal"
    if path.startswith("vs/") or path.startswith("best/") or path.startswith("gifts/") or path.startswith("black-friday-fragrance-deals/"): return "compare"
    if path.startswith("dupes/") and path!="dupes/index.html": return "hub"
    if path.startswith("dupe/"): return "dupe"
    return None
def also_line(d):
    a=d.get("also")
    if not a or a.get("price") is None or not a.get("url"): return ""
    return f"<div class='also'>also at {ext_a(a['url'], e(a['retailer']), placement='also')} · ${a['price']:.2f}</div>"
# Neutral stand-in when the retailer data has no photo. Not a product picture.
_PLACEHOLDER_SVG='<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400"><rect width="400" height="400" fill="#f4f1ec"/><rect x="168" y="88" width="64" height="16" rx="3" fill="#d5cfc7"/><path d="M156 110h88v188a30 30 0 0 1-30 30h-28a30 30 0 0 1-30-30V110z" fill="#e6e0d8" stroke="#c8c2ba" stroke-width="3"/><text x="200" y="358" text-anchor="middle" font-family="system-ui,sans-serif" font-size="18" fill="#7a7480">No photo</text></svg>'
PLACEHOLDER_SRC="data:image/svg+xml,"+urllib.parse.quote(_PLACEHOLDER_SVG)
MISSING_PHOTOS=[]
def retailer_image(d):
    """Photo already stored on the product: retailer feed or the retailer's own image URL. Never macys.com."""
    url=(d.get("image") or "").strip() if isinstance(d.get("image"),str) else ""
    if not url.startswith(("http://","https://")): return ""
    host=(urllib.parse.urlparse(url).hostname or "").lower()
    if not host or "macys" in host: return ""
    return url
def product_alt(d):
    """'<Brand> <Name> <size>' from the fields we already store."""
    if d.get("brand") and d.get("name"): name=fullname(d)
    else: name=(d.get("dupe") or d.get("name") or "Fragrance").strip()
    size=sz(d.get("size") or "")
    if size and size.lower() not in name.lower(): return f"{name} {size}"
    return name
def card_img(d, eager=False, alt=None):
    """Same img markup as the roundup cards: dimensions, lazy (unless the LCP slot), async decode."""
    src=retailer_image(d)
    if not src:
        src=PLACEHOLDER_SRC
        key=d.get("id") or product_alt(d)
        if key not in {row["key"] for row in MISSING_PHOTOS}:
            MISSING_PHOTOS.append({"key":key,"label":product_alt(d),"brand":d.get("brand") or "","name":d.get("name") or d.get("dupe") or "","size":sz(d.get("size") or "")})
    ld='fetchpriority="high"' if eager else 'loading="lazy"'
    alt=product_alt(d) if alt is None else alt
    return f'<img {ld} decoding="async" src="{e(src)}" alt="{e(alt)}" width="400" height="400">'
def card(d,eager=False):
    return f"""<article class="card">{card_img(d, eager, alt=fullname(d))}
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
    text+=", compared across authorized retailers."
    if d.get("contents"):
        text+=" "+str(d["contents"]).strip().rstrip(".")+"."
    return text
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
    img=retailer_image(d)
    if img: product["image"]=img
    offers=aggregate_offer(d)
    if offers: product["offers"]=offers
    return product
def itemlist(ds,name):
    items=[]
    for i,d in enumerate(ds):
        label=fullname(d) if d.get("contents") else f"{fullname(d)} {d['size']}".strip()
        item=prod_ld(d, name=label, brand=canon(d["brand"]))
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
 ]+[dict(r,items=[BYID[i['id']] for i in r['items'] if i['id'] in BYID and BYID[i['id']]['price']<r.get('max_price',1e9)],notes={i['id']:i['notes'] for i in r['items']}) for r in CFG.get("roundups",[])] if len(r["items"])>=3]
def roundups_of(d): return [r for r in ROUNDUPS if d in r['items']]
def _deal_blob(d):
    return " ".join(str(d.get(k) or "") for k in ("name","brand","type","size","retailer","url")).lower()
def early_gift_ok(d):
    """A checked bottle we can recommend. Testers, decants, and Amazon stay out."""
    if d.get("in_stock") is False: return False
    if isinstance(d.get("price"), bool) or not isinstance(d.get("price"), (int, float)): return False
    if not d.get("url") or not d.get("retailer"): return False
    blob=_deal_blob(d)
    if re.search(r"\b(tester|testers|decant|decants)\b", blob): return False
    host=(urllib.parse.urlparse(d.get("url") or "").hostname or "").lower()
    if "amazon" in blob or "amazon." in host or host.endswith("amazon.com"): return False
    return True
def early_mini(d):
    blob=_deal_blob(d)
    if re.search(r"\b(mini|minis|miniature|travel|travel-size|travelsize|rollerball|roller-ball)\b", blob): return True
    o=oz(d.get("size") or "")
    return o is not None and o<1
def _row_key(d):
    return (d.get("id"), sz(d.get("size") or ""))
def _looks_like_set(d):
    """Boxed set. A mini bottle is not one, even when the word miniature appears beside a single size."""
    if d.get("kind")=="mini": return False
    if d.get("kind")=="set": return True
    blob=_deal_blob(d)
    if any(s in blob for s in ("gift set","gift-set","coffret","discovery set","mini set")): return True
    return bool(re.search(r"\b\d+\s*-?\s*(pc|piece|pcs)\b", blob) and "set" in blob)
def _catalog_travel():
    """Minis, rollerballs, and travel sizes already checked in the gift catalog. No invented rows."""
    rows=[]
    for d in D.get("gifts") or []:
        if _looks_like_set(d) or not early_gift_ok(d): continue
        if d.get("kind")=="mini":
            rows.append(d); continue
        blob=_deal_blob(d)
        if re.search(r"\b(mini|minis|miniature|travel(?:\s*|-)?size|travelsize|roller-?ball)\b", blob):
            rows.append(d)
    return rows
NOTE_BY_ID={}
for _r in CFG.get("roundups",[]):
    for _it in _r.get("items",[]):
        if _it.get("id") and _it.get("notes"): NOTE_BY_ID.setdefault(_it["id"], _it["notes"])
def guide_rows(spec):
    rows=[d for d in deals if early_gift_ok(d)]
    if spec.get("include_travel"):
        # Same retailer handle can be a full bottle in deals and a smaller mini in the catalog.
        seen={_row_key(d) for d in rows}
        for d in _catalog_travel():
            key=_row_key(d)
            if key in seen: continue
            rows.append(d)
            seen.add(key)
    if spec.get("gender"): rows=[d for d in rows if d["gender"]==spec["gender"]]
    if spec.get("genders"): rows=[d for d in rows if d["gender"] in spec["genders"]]
    cap=spec.get("max_price")
    if isinstance(cap,(int,float)) and not isinstance(cap,bool):
        if spec.get("max_price_inclusive"):
            rows=[d for d in rows if d["price"]<=cap]
        else:
            rows=[d for d in rows if d["price"]<cap]
    floor_price=spec.get("min_price")
    if isinstance(floor_price,(int,float)) and not isinstance(floor_price,bool): rows=[d for d in rows if d["price"]>=floor_price]
    floor=spec.get("min_was")
    if isinstance(floor,(int,float)) and not isinstance(floor,bool):
        rows=[d for d in rows if isinstance(d.get("was"),(int,float)) and not isinstance(d.get("was"),bool) and d["was"]>=floor]
    if spec.get("exclude_mini"): rows=[d for d in rows if not early_mini(d)]
    if spec.get("exclude_set"): rows=[d for d in rows if not _looks_like_set(d)]
    wanted=spec.get("roundups")
    if wanted:
        # Only bottles already on a notes roundup. A note line exists for each of those ids.
        known={r["slug"]: r for r in CFG.get("roundups", [])}
        missing=[s for s in wanted if s not in known]
        if missing:
            raise SystemExit("gift guide unknown roundup: "+", ".join(missing))
        ids=set()
        for s in wanted:
            for it in known[s].get("items") or []:
                if it.get("id") and it.get("notes"): ids.add(it["id"])
        rows=[d for d in rows if d.get("id") in ids]
    rows.sort(key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))
    return rows
def _format_cap(raw, cap):
    """Fill {cap} in a guide's copy. The number is the cap this build actually used."""
    token=f"{cap:g}"
    spec=dict(raw)
    spec["max_price"]=cap
    for key in ("title","chip","filled_label","empty","empty_desc","intro"):
        if isinstance(spec.get(key), str): spec[key]=spec[key].replace("{cap}", token)
    if spec.get("faq"):
        spec["faq"]=[[q.replace("{cap}", token), a.replace("{cap}", token)] for q,a in spec["faq"]]
    return spec
def materialize_guide(raw):
    if "{cap}" not in json.dumps(raw):
        return dict(raw, picks=guide_rows(raw))
    spec=_format_cap(raw, raw.get("max_price"))
    picks=guide_rows(spec)
    need=raw.get("min_picks")
    fb=raw.get("fallback_max_price")
    if (isinstance(need, int) and not isinstance(need, bool)
            and isinstance(fb, (int, float)) and not isinstance(fb, bool)
            and len(picks)<need):
        spec=_format_cap(raw, fb)
        picks=guide_rows(spec)
        print(f"gift guide {spec['slug']}: {need} picks needed, cap raised to ${fb:g} ({len(picks)} picks)")
    prices=[d["price"] for d in picks]
    span=f"${min(prices):.2f}–${max(prices):.2f}" if prices else "none"
    print(f"gift guide {spec['slug']}: {len(picks)} picks, {span}, cap ${spec['max_price']:g}")
    return dict(spec, picks=picks)
GIFT_GUIDES=[materialize_guide(spec) for spec in CFG.get("gift_guides",[])]
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
]+[(g["slug"], g.get("chip") or g["title"]) for g in GIFT_GUIDES]
# Filled as each gift subpage is written, then spliced into the hub, homepage,
# and sibling pages. The sitemap is the same page() pass, so a new guide is linked
# from the build that adds it.
GIFT_SUBPAGES=[]
# (slug, h1, picks actually rendered) for each /gifts/<slug>/ page. The hub is not included.
GIFT_PAGE_PICKS=[]
GIFT_HUB_MARK="<!--gift-guides-->"
GIFT_HOME_MARK="<!--holiday-gift-guides-->"
GIFT_MORE_MARK="<!--more-gift-guides-->"
BRAND_GIFT_MARK="<!--brand-gift-guides-->"
DUPE_GIFT_MARK="<!--dupe-gift-guides-->"
FRAGRANCE_GIFT_MARK="<!--fragrance-gift-guides-->"
VS_GIFT_MARK="<!--vs-gift-guides-->"
# (relative path, comparison) for each /vs/ page this build wrote.
VS_PAGES=[]
# (relative path, deal) for each /fragrance/ page this build wrote.
FRAGRANCE_PAGES=[]
# Compact homepage set. Titles come from GIFT_SUBPAGES, not from this tuple.
HOME_GIFT_SLUGS=("for-him","for-her","under-50","perfume-gifts-for-her-under-50","best-mens-cologne-under-40","holiday-gift-sets","fragrance-gifts-for-teens","fragrance-stocking-stuffers-under-25")
def register_gift_subpage(slug, title):
    if not slug or not str(title or "").strip():
        raise SystemExit("gift guide missing a slug or page title")
    if any(s==slug for s,_ in GIFT_SUBPAGES):
        raise SystemExit(f"gift guide registered twice: {slug}")
    GIFT_SUBPAGES.append((slug, str(title).strip()))
use_sid("home")
page("index.html",fit([f"Perfume & Cologne Deals Today: Up to {max(d['pct_off'] for d in deals)}% Off | {NAME}",f"Fragrance Deals Today: Up to {max(d['pct_off'] for d in deals)}% Off | {NAME}"]),
 f"{len(deals)} verified deals on authentic designer perfume & cologne from ${min(d['price'] for d in deals):.2f}, up to {max(d['pct_off'] for d in deals)}% off at authorized retailers. Checked {upd:%b %-d}, plus the best dupes.",
 f"<h1>Today's best designer fragrance deals</h1><p class='sub'>{len(deals)} live deals on authentic bottles · last checked {upd_h} · sorted by % off</p>"
 +BREVO_FORM
 +f"<div class='grid'>{''.join(card(d,i<2) for i,d in enumerate(deals))}</div><p class='chips'><a href='{PREFIX}/gifts/'>Holiday fragrance gifts</a>"
 +"".join(f"<a href='{PREFIX}/gifts/{slug}/'>{e(label)}</a>" for slug,label in SEO_GIFTS)+"</p>"+GIFT_HOME_MARK+bestchips()
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
    gchip="".join(f"<a href='{PREFIX}/gifts/{gu['slug']}/'>{e(gu.get('chip') or gu['title'])}</a>" for gu in GIFT_GUIDES if any(d["gender"]==g for d in gu["picks"]))
    tb=", ".join(dict.fromkeys(canon(d['brand']) for d in ds))
    tb=tb if len(tb)<50 else tb[:tb.rfind(",",0,50)]+" & more"
    mx=max(d['pct_off'] for d in ds)
    lo_p=min(d['price'] for d in ds)
    if len(ds)<=3:
        named=", ".join(f"{d['name']} ${d['price']:.2f}" for d in sorted(ds, key=lambda d:d['price']))
        gdesc=fit([
            f"{len(ds)} authentic {label.lower()} deals: {named}. Up to {mx}% off at authorized retailers. Checked {upd:%b %-d, %Y}.",
            f"{len(ds)} {label.lower()} deals: {named}. Up to {mx}% off. Checked {upd:%b %-d, %Y}.",
            f"{len(ds)} authentic {label.lower()} deals from ${lo_p:.2f}, up to {mx}% off: {tb}. Checked {upd:%b %-d}.",
        ],160)
    else:
        gdesc=f"{len(ds)} authentic {label.lower()} deals from ${lo_p:.2f}, up to {mx}% off at authorized retailers: {tb}. Checked {upd:%b %-d}."
    page(f"{g}/index.html",fit([f"{label} Deals Today ({upd:%b %-d}): Up to {mx}% Off | {NAME}",f"{label} Deals: Up to {mx}% Off Today | {NAME}",f"{label} Deals Today ({upd:%b %-d}): Up to {mx}% Off"]),
      gdesc,
      f"<h1>{label} deals</h1><p class='sub'>{len(ds)} live · checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{BREVO_FORM}{bestchips()}"+(f"<p class='chips'>{gchip}</p>" if gchip else ""),[itemlist(ds,label+" deals")])
brands=sorted({canon(d["brand"]) for d in deals})
for b in brands:
    ds=[d for d in deals if canon(d["brand"])==b]
    use_sid("brand", bslug(b))
    def short_nm(d):
        n=fullname(d).replace(b+" ","",1)
        return d['name'] if n in ("Perfume","Cologne","Eau de Toilette","Eau de Parfum") else n  # "Coach Cologne", not "Cologne"
    nm=", ".join(short_nm(d) for d in ds[:2])+(" & more" if len(ds)>2 else "")
    mx=max(d['pct_off'] for d in ds)
    one=ds[0]
    genders={d["gender"] for d in ds}
    kind="Cologne" if genders=={"men"} else "Perfume" if genders=={"women"} else "Fragrance" if genders=={"unisex"} else "Perfume & Cologne"
    if len(ds)==1:
        bm=fit([f"{fullname(one)} {sz(one['size'])} for ${one['price']:.2f} at {one['retailer']}, {one['pct_off']}% off"+(f" the {one['was_label']} price" if one.get('was_label') else f" its ${one['was']:.2f} list price")+f". Our only verified {b} deal today, checked {upd:%b %-d, %Y}.",
                f"{fullname(one)} {sz(one['size'])} for ${one['price']:.2f} at {one['retailer']}, {one['pct_off']}% off. Our only verified {b} deal today, checked {upd:%b %-d}.",
                f"{fullname(one)} {sz(one['size'])}: ${one['price']:.2f} at {one['retailer']}, {one['pct_off']}% off. Checked {upd:%b %-d}."],160)
    else:
        lo_p=min(d['price'] for d in ds); hi_p=max(d['price'] for d in ds)
        bm=fit([
            f"{len(ds)} verified {b} {kind.lower()} deals from ${lo_p:.2f} to ${hi_p:.2f} ({nm}), up to {mx}% off. Checked {upd:%b %-d, %Y}.",
            f"{len(ds)} verified {b} deals from ${lo_p:.2f} ({nm}), up to {mx}% off. Checked {upd:%b %-d, %Y}.",
            f"{len(ds)} verified {b} fragrance deals from ${lo_p:.2f} ({nm}). Authentic, price-checked {upd:%b %-d, %Y}.",
        ],160)
    page(f"brands/{bslug(b)}/index.html",fit([f"{b} {kind} Deals: Up to {mx}% Off Today | {NAME}",f"{b} {kind} Deals: Up to {mx}% Off Today",f"{b} {kind} Deals: Up to {mx}% Off",f"{b} Fragrance Deals: Up to {mx}% Off"]),
      bm,
      f"<h1>{e(b)} deals</h1><p class='sub'>checked {upd_h}</p><div class='grid'>{''.join(card(d) for d in ds)}</div>{BRAND_GIFT_MARK}{BREVO_FORM}",[itemlist(ds,b+" deals")])
page("brands/index.html",fit([f"Fragrance Deals by Brand: {len(brands)} Designer Brands on Sale Today | {NAME}",f"Fragrance Deals by Brand: {len(brands)} Designer Brands on Sale Today"]),
 f"{len(brands)} designer brands with checked perfume and cologne deals, including {', '.join(brands[:3])}. Authorized retailers only, prices checked daily.",
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
    full=fullname(d); s=slug(f"{d['brand']} {d['name']}"); use_sid("deal", s); KW+= [f"{full.lower()} cheapest price",f"{full.lower()} sale",f"{full.lower()} {sz(d['size']).lower()} deal"]
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
      +FRAGRANCE_GIFT_MARK
      +faqhtml(qs)+"<h2>Similar deals today</h2><div class='grid'>"+"".join(card(x) for x in others)+"</div>")
    short=re.sub(r"( Spray)? (Cologne|Perfume|Unisex Fragrance)$","",full); P=f"${d['price']:.2f}"; Z=sz(d['size'])
    save=d['was']-d['price']
    was_bit=(f"{d['pct_off']}% below the ${d['was']:.2f} {d['was_label']} price" if d.get('was_label') else f"{d['pct_off']}% off the ${d['was']:.2f} list price")
    frag_rel=f"fragrance/{s}/index.html"
    page(frag_rel,fit([f"{full} {Z} Sale: {P} ({d['pct_off']}% Off) – Cheapest Price {upd:%b %Y}",f"{full} {Z} Sale: {P} ({d['pct_off']}% Off)",f"{short} {Z} Sale: {P} ({d['pct_off']}% Off)",f"{short} {Z}: {P} ({d['pct_off']}% Off)",f"{short}: {P} ({d['pct_off']}% Off)",f"{short.replace(canon(d['brand'])+' ','',1).replace(d['brand']+' ','',1)} {Z}: {P} ({d['pct_off']}% Off)"]),
      fit([f"{full} {Z} is {P} at {d['retailer']}, {was_bit} (save ${save:.2f}). Sealed bottle, checked {upd:%b %-d, %Y}.",
           f"{full} {Z} is {P} at {d['retailer']}, {was_bit}. Sealed, checked {upd:%b %-d, %Y}.",
           f"{full} {Z} for {P} at {d['retailer']} ({was_bit}). Checked {upd:%b %-d, %Y}."],160),body,
      [prod_ld(d, name=f"{full} {d['size']}", brand=d['brand']),faqld(qs)])
    FRAGRANCE_PAGES.append((frag_rel, d))
def nohouse(n):
    """Name without the house prefix (Armaf/Lattafa/MFK/YSL...), for titles that would run past 60 chars."""
    w=re.sub(r' [(].*?[)]','',n).split(); k=2 if w[0] in ("Al","Ariana") else 1
    return " ".join(w[k:]) if len(w)>k else n
def house(name):
    w=(name or "").split()
    if not w: return ""
    return " ".join(w[:2]) if w[0] in ("Al","Ariana") else w[0]
def original_house(name):
    """Designer house of the fragrance being copied. Chanel is named mid-string on Bleu de Chanel."""
    n=(name or "").lower()
    if "chanel" in n: return "chanel"
    if n.startswith("ysl"): return "ysl"
    if n.startswith("mfk"): return "mfk"
    if n.startswith("jean paul"): return "jean paul gaultier"
    return (n.split() or [""])[0]
def dupe_href(x):
    return f"{PREFIX}/dupe/{slug(x['original']+' dupe '+x['dupe'])}/"
def related_dupe_picks(d, limit=6):
    """Same original, then the same hub or designer house, then the dupe's own house, then the rest."""
    others=[x for x in D["dupes"] if x is not d]
    hb=hub_of(d)
    in_hub={id(x) for x in (hb["items"] if hb else [])}
    oh=original_house(d.get("original") or "")
    dh=house(d.get("dupe") or "").lower()
    def tier(x):
        if x.get("original")==d.get("original"): return 0
        if id(x) in in_hub: return 1
        if oh and original_house(x.get("original") or "")==oh: return 2
        if dh and house(x.get("dupe") or "").lower()==dh: return 3
        return 4
    return sorted(others, key=lambda x:(tier(x), D["dupes"].index(x)))[:limit]
def chip_section(heading, pairs):
    links="".join(f"<a href='{href}'>{e(label)}</a>" for href, label in pairs)
    return f"<section class='box'><h2 style='margin-top:0'>{e(heading)}</h2><div class='chips'>{links}</div></section>"
def related_dupes_section(d):
    pairs=[]
    hb=hub_of(d)
    if hb: pairs.append((f"{PREFIX}/dupes/{hb['slug']}/", hb["title"]))
    for x in related_dupe_picks(d, 6):
        pairs.append((dupe_href(x), f"{x['original']} → {x['dupe']}"))
    pairs.append((f"{PREFIX}/dupes/", "All dupes"))
    return chip_section("Related dupes", pairs)+DUPE_GIFT_MARK
def _dupe_words(s):
    return re.sub(r"[^a-z0-9]+"," ", str(s or "").lower())
def dupe_audience(d):
    """men / women / unisex from the product name, the priced URL, or the retailer handle.

    A cited cologne roundup is used only when those fields say nothing.
    """
    def hit(text):
        if re.search(r"\b(for women|woman|women|mademoiselle)\b", text): return "women"
        if re.search(r"\b(for men|homme|male|man)\b", text): return "men"
        if re.search(r"\bunisex\b", text): return "unisex"
        return None
    named=hit(_dupe_words(f"{d.get('dupe') or ''} {d.get('original') or ''}"))
    if named in ("men","women"): return named
    url_hit=hit(_dupe_words(d.get("url")))
    handle_hit=hit(_dupe_words(d.get("handle")))
    if "unisex" in (url_hit, handle_hit) and "women" not in (url_hit, handle_hit):
        return "unisex"
    if url_hit: return url_hit
    if handle_hit: return handle_hit
    if named: return named
    if re.search(r"\bcologne\b", _dupe_words(" ".join(d.get("sources") or []))): return "men"
    return None
# Scent families are the note roundups already in config. Price roundups are not families.
_SCENT_FAMILY_SLUGS=(
    "fresh-citrus-cologne-deals","vanilla-sweet-fragrance-deals","floral-perfume-deals",
    "woody-amber-cologne-deals","warm-spicy-cologne-deals","fresh-perfume-deals-under-50",
)
_NOTE_STOP=frozenset("""
with from that this into over under than then and the for notes note base accord accords
scent scents listed range checked overall scored altscent scentfile dupenote per adds closer
read twist playful office polished spray eau parfum toilette cologne perfume fragrance
unisex women woman price today bottle more most other their they have been were which while
where about after before black white green pink blue down softer airy rich clean cool warm
play widely original alternative community dry aroma aromas smell smells like very just
only also each both same your our not but can may
""".split())
def _note_tokens(text):
    text=re.sub(r"https?://\S+"," ", str(text or ""))
    text=re.sub(r"\$\d[\d.,]*"," ", text)
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _NOTE_STOP}
def _build_scent_index():
    known={r["slug"]: r for r in CFG.get("roundups") or []}
    vocab={}; members={}
    for slug in _SCENT_FAMILY_SLUGS:
        row=known.get(slug)
        if not row: continue
        words=set(); ids=set()
        for it in row.get("items") or []:
            if it.get("id"): ids.add(it["id"])
            words |= _note_tokens(it.get("notes"))
        if words:
            vocab[slug]=words
            members[slug]=ids
    return vocab, members
_FAMILY_VOCAB,_FAMILY_MEMBERS=_build_scent_index()
_DEAL_FAMILIES={}
for _slug,_ids in _FAMILY_MEMBERS.items():
    for _i in _ids: _DEAL_FAMILIES.setdefault(_i, set()).add(_slug)
_FAMILY_WORDS=set().union(*_FAMILY_VOCAB.values()) if _FAMILY_VOCAB else set()
DUPE_DEAL_TARGET=6
DUPE_DEAL_PICKS={}
def _card_deal_ok(d):
    """A deals.json row the shared card can render. No price is filled in here."""
    if d.get("in_stock") is False: return False
    if isinstance(d.get("price"), bool) or not isinstance(d.get("price"), (int, float)): return False
    if isinstance(d.get("was"), bool) or not isinstance(d.get("was"), (int, float)): return False
    if isinstance(d.get("pct_off"), bool) or not isinstance(d.get("pct_off"), (int, float)): return False
    return bool(d.get("url") and d.get("retailer") and d.get("brand") and d.get("name") and d.get("id"))
def _is_exact_deal(dupe, deal):
    """True when this deals.json row is the dupe or the original, not a neighbor."""
    handle=dupe.get("handle")
    if handle and handle==deal.get("id"): return True
    blob=_dupe_words(f"{deal.get('brand') or ''} {deal.get('name') or ''}").strip()
    if not blob: return False
    for raw in (dupe.get("dupe"), dupe.get("original")):
        phrase=_dupe_words(raw).strip()
        if len(phrase)>=8 and phrase in blob: return True
    return False
def _scent_blob(dupe):
    """This pair's notes. When they name no family, borrow a closer original's notes."""
    blob=dupe.get("notes") or ""
    if _note_tokens(blob) & _FAMILY_WORDS: return blob
    orig=dupe.get("original") or ""
    extra=[]
    for other in D["dupes"]:
        if other is dupe: continue
        oth=other.get("original") or ""
        if oth and oth!=orig and (orig.startswith(oth) or oth.startswith(orig)):
            extra.append(other.get("notes") or "")
    return " ".join([blob]+extra)
def _house_keys(dupe):
    keys=set()
    for key in (house(dupe.get("dupe") or "").lower().strip(), original_house(dupe.get("original") or "").lower().strip()):
        if len(key)>=3: keys.add(key)
    return keys
def _brand_match(deal, keys):
    b=(deal.get("brand") or "").lower().strip()
    if len(b)<3: return False
    return any(b==k or b.startswith(k+" ") or k.startswith(b+" ") for k in keys)
def _dupe_families(tokens):
    return {slug for slug, words in _FAMILY_VOCAB.items() if tokens & words}
def _score_deal(dupe, deal, tokens, families, keys, aud):
    score=0; why=set()
    if _brand_match(deal, keys):
        score+=6; why.add("brand")
    g=deal.get("gender")
    if aud in ("men","women") and g==aud:
        score+=3; why.add("gender")
    elif aud in ("men","women") and g=="unisex":
        score+=1; why.add("gender")
    elif aud=="unisex" and g=="unisex":
        score+=2; why.add("gender")
    overlap=tokens & _note_tokens(NOTE_BY_ID.get(deal.get("id"), ""))
    if overlap:
        score+=2*len(overlap); why.add("scent")
    if families and (_DEAL_FAMILIES.get(deal.get("id"), set()) & families):
        score+=2; why.add("scent")
    return score, why
def pick_dupe_deals(dupe):
    """Exact deals.json rows, then similar rows until the page has a full card grid.

    Similar rows stay inside the dupe's gender when that pool is large enough.
    Rank is shared brand, then gender, then scent-family notes already stored on the deal.
    """
    feed=[d for d in deals if _card_deal_ok(d)]
    exact=[d for d in feed if _is_exact_deal(dupe, d)]
    exact.sort(key=lambda d:(-(d.get("pct_off") or 0), d["price"], d["id"]))
    used={d["id"] for d in exact}
    rest=[d for d in feed if d["id"] not in used]
    need=max(0, DUPE_DEAL_TARGET-len(exact))
    if not exact: need=DUPE_DEAL_TARGET
    tokens=_note_tokens(_scent_blob(dupe))
    families=_dupe_families(tokens)
    keys=_house_keys(dupe)
    aud=dupe_audience(dupe)
    pool=rest
    if aud in ("men","women"):
        pref=[d for d in rest if d.get("gender") in (aud, "unisex")]
        if len(pref)>=need: pool=pref
    def ranked(rows):
        scored=[(*_score_deal(dupe, d, tokens, families, keys, aud), d) for d in rows]
        scored.sort(key=lambda row:(-row[0], -(row[2].get("pct_off") or 0), row[2]["price"], row[2]["id"]))
        return scored
    chosen=ranked(pool)[:need]
    similar=[row[2] for row in chosen]
    reasons=set().union(*(row[1] for row in chosen)) if chosen else set()
    if len(exact)+len(similar)<DUPE_DEAL_TARGET:
        have={d["id"] for d in similar}
        for score, why, d in ranked([d for d in rest if d["id"] not in have]):
            if len(exact)+len(similar)>=DUPE_DEAL_TARGET: break
            similar.append(d); reasons |= why
    if len(exact)+len(similar)<DUPE_DEAL_TARGET:
        raise SystemExit(f"dupe page for {dupe.get('dupe')}: {len(exact)+len(similar)} deal cards, need {DUPE_DEAL_TARGET}")
    return exact, similar, reasons
def dupe_deals_html(d):
    """Deal cards for one dupe page. Prices come only from the deals passed to card()."""
    exact, similar, reasons=pick_dupe_deals(d)
    DUPE_DEAL_PICKS[id(d)]={"exact":exact,"similar":similar,"reasons":reasons}
    parts=[]
    if exact:
        lead="These match the dupe or the original in today's deals. Prices are the ones we already checked."
        if "$" in lead: raise SystemExit("dupe deal copy contains a price")
        parts.append("<section class='box'><h2 style='margin-top:0'>Matching deals in stock now</h2>"
            f"<p>{e(lead)}</p><div class='grid'>"+"".join(card(x) for x in exact)+"</div></section>")
    if similar:
        if exact:
            lead="These bottles are from the deals we already checked, ranked by shared gender, scent family, or brand. They are not the dupe or the original."
        else:
            lead="The exact dupe and the original are not in today's deals. These bottles are from the deals we already checked, ranked by shared gender, scent family, or brand."
        if "$" in lead: raise SystemExit("dupe deal copy contains a price")
        parts.append("<section class='box'><h2 style='margin-top:0'>Similar deals in stock now</h2>"
            f"<p>{e(lead)}</p><div class='grid'>"+"".join(card(x) for x in similar)+"</div></section>")
    print(f"dupe deals: {d.get('dupe')} exact={len(exact)} similar={len(similar)} ({','.join(sorted(reasons)) or 'feed'})")
    return "".join(parts)
DUPE_PAGES=[]
for d in D["dupes"]:
    s=slug(f"{d['original']} dupe {d['dupe']}"); use_sid("dupe", s); o=d['original']
    KW+=[f"{o.lower()} dupe",f"best cheap {o.lower()} dupe {upd.year}",f"{d['dupe'].lower()} vs {o.lower()}"]
    pr=f"${d['price']:.2f} for {d['size']} at {d['retailer']}" if d['price'] else "not yet price-verified by us"
    qs=[(f"What is the best cheap {o} dupe in {upd.year}?",f"{d['dupe']} is one of the most-cited affordable alternatives to {o}: {d['notes']}. Today: {pr}."),
        (f"Does {d['dupe']} smell like {o}?",f"Community rankings rate it as close ({d['notes']}). It is an original 'inspired by' fragrance, not a counterfeit; expect differences in the dry-down."),
        (f"Where can I buy {d['dupe']} cheapest?",f"The lowest price we verified is {pr}" + (f" (checked {upd_h})." if d['price'] else ". Check back; we add prices only after verifying them."))]
    body=(f"<h1>Best {e(o)} dupe: {e(d['dupe'])}</h1><p class='sub'>{e(d['notes'])} · {('<b class=price>$%.2f</b> today at %s' % (d['price'],e(d['retailer']))) if d['price'] else 'price not verified yet'}</p>"
      +((buy(d['url'],d['retailer'])+also_line(d)) if d['price'] else "")
      +f"<div class='box'><h2 style='margin-top:0'>{e(o)} vs {e(d['dupe'])}</h2><table><thead><tr><th></th><th>{e(o)}</th><th>{e(d['dupe'])}</th></tr></thead><tbody><tr><td>Price</td><td>{e(d.get('original_price') or 'varies')}</td><td>{('$%.2f (%s)' % (d['price'],e(d['size']))) if d['price'] else '—'}</td></tr><tr><td>Profile</td><td colspan=2>{e(d['notes'])}</td></tr><tr><td>Sources</td><td colspan=2>{' '.join((f'<a href="{e(affiliate_url(x, "src"))}" rel="nofollow sponsored noopener" target="_blank">[{i+1}]</a>' if is_perfumania(x) else f'<a href={e(x)} rel=noopener target=_blank>[{i+1}]</a>') for i,x in enumerate(d['sources']))}</td></tr></tbody></table></div>"
      +((f"<div class='box'><h2 style='margin-top:0'>Where to buy {e(d['dupe'])} cheapest</h2><table><thead><tr><th>Retailer</th><th>Size</th><th>Price</th><th>Checked</th></tr></thead><tbody>{comprows(d)}</tbody></table></div>") if d.get('comps') else "")+dupe_deals_html(d)+faqhtml(qs)+related_dupes_section(d))
    DUPE_PAGES.append((f"dupe/{s}/index.html", d))
    lds=[faqld(qs)]+([prod_ld(d, name=d['dupe'], brand=d['dupe'].split()[0])] if d['price'] else [])
    PR=(f" ${d['price']:.2f}" if d['price'] else "")
    bare=re.sub(r' [(].*?[)]','',o)
    note=d['notes'].rstrip('.')
    if d['price']:
        dmeta=f"{d['dupe']} vs {o}: {note.split(';')[0].rstrip('.')}. ${d['price']:.2f} for {d['size']} at {d['retailer']} today. Cited sources, authentic bottles only."
    else:
        dmeta=fit([f"{d['dupe']} vs {o}: {note}. No live retailer price verified yet. Cited sources, authentic bottles only.",
                   f"{d['dupe']} vs {o}: {note.split(';')[0].rstrip('.')}. No live price verified yet. Cited sources only."],160)
    page(f"dupe/{s}/index.html",fit([f"Best {o} Dupe {upd.year}: {d['dupe']}{PR}",f"Best {o} Dupe: {d['dupe']}{PR}",f"{o} Dupe: {d['dupe']}{PR}",f"{bare} Dupe: {nohouse(d['dupe'])}{PR}" if d['price'] else "",f"{nohouse(o)} Dupe: {nohouse(d['dupe'])}{PR}" if d['price'] else "",f"{o} Dupe: {d['dupe']}",f"{bare} Dupe: {re.sub(r' [(].*?[)]','',d['dupe'])}",f"{o} Dupe: {nohouse(d['dupe'])}",f"{nohouse(o)} Dupe: {nohouse(d['dupe'])}"]),
      dmeta,body,lds)
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
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/best/{x['slug']}/'>{e(x['title'])}</a>" for x in others)+"".join(f"<a href='{PREFIX}/gifts/{g['slug']}/'>{e(g.get('chip') or g['title'])}</a>" for g in GIFT_GUIDES if any(d in g['picks'] for d in ds))+f"<a href='{PREFIX}/men/'>All men's deals</a><a href='{PREFIX}/women/'>All women's deals</a><a href='{PREFIX}/dupes/'>Designer dupes</a></p>")
    il={"@context":"https://schema.org","@type":"ItemList","name":r['title'],"numberOfItems":n,"itemListElement":[{"@type":"ListItem","position":i+1,"item":offer_item(d, f"{fullname(d)} {d['size']}", d['brand'])} for i,d in enumerate(ds)]}
    CP=f"${cheap['price']:.2f}"
    page(f"best/{r['slug']}/index.html",fit([f"{r['title']} Today ({upd:%b %-d}): {n} Authentic Picks | {NAME}",f"{r['title']} Today: {n} Picks From {CP}",f"{r['title']}: {n} Picks From {CP}",f"{r['title']} ({upd:%b %Y})"]),
      fit([f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off, from ${cheap['price']:.2f} ({fullname(cheap)}). Ranked by price per ounce, checked {upd:%b %-d, %Y}.",
           f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off, from {CP} ({fullname(cheap)}). Checked {upd:%b %-d}.",
           f"{n} authentic {r['who']} {N}s {SC}, all 15%+ off at authorized retailers, from {CP}. Ranked by price per ounce, checked {upd:%b %-d}."],160),body,[il,faqld(qs)])
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
    names=", ".join(nohouse(x['dupe']) for x in ms)
    noted="; ".join(f"{nohouse(x['dupe'])} ({x['notes'].split(';')[0].rstrip('.')})" for x in ms)
    priced=(f" Prices from ${cheapest['price']:.2f}." if cheapest else " No live price verified yet.")
    page(f"dupes/{h['slug']}/index.html",fit([f"{h['title']} {upd.year}: {len(ms)} Clones Compared{FR} | {NAME}",f"{h['title']} {upd.year}: {len(ms)} Clones Compared{FR}",f"{h['title']} {upd.year}: {len(ms)} Clones{FR}",f"{h['title']} {upd.year}"]),
      fit([f"{len(ms)} {T} dupes: {noted}.{priced} Checked {upd:%b %-d, %Y}.",
           f"{len(ms)} {T} dupes: {names}.{priced} Checked {upd:%b %-d, %Y}.",
           f"{len(ms)} {T} dupes from {houses}.{priced} Profiles and cited sources, checked {upd:%b %-d, %Y}.",
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
      +VS_GIFT_MARK
      +"<p class='chips'>"+"".join(f"<a href='{PREFIX}/best/{x['slug']}/'>{e(x['title'])}</a>" for x in ROUNDUPS if A in x['items'] or B in x['items'])+"".join(f"<a href='{PREFIX}/vs/{x['slug']}/'>{e(x['title'])}</a>" for x in VS if x is not v)+f"<a href='{PREFIX}/{A['gender']}/'>All {A['gender']}'s deals</a><a href='{PREFIX}/brands/{bslug(A['brand'])}/'>All {e(canon(A['brand']))} deals</a></p>")
    CP=f"${cheaper['price']:.2f}"
    vs_rel=f"vs/{v['slug']}/index.html"
    page(vs_rel,fit([f"{T}: Which to Buy? Prices From {CP} ({upd:%b %Y}) | {NAME}",f"{T}: Which to Buy? From {CP}",f"{T}: Which Is Better? From {CP}",f"{T} Compared: From {CP}",f"{T}: From {CP}",f"{T}: Which to Buy?",f"{T} Compared"]),
      fit([f"{fa} (${A['price']:.2f}, {sz(A['size'])}) vs {fb} (${B['price']:.2f}, {sz(B['size'])}): price per ounce, concentration and key notes compared. Checked {upd:%b %-d, %Y}.",
           f"{T}: ${A['price']:.2f} ({sz(A['size'])}) vs ${B['price']:.2f} ({sz(B['size'])}) today. Price per ounce, concentration, key notes and which to buy. Checked {upd:%b %-d}.",
           f"{T}: ${A['price']:.2f} ({sz(A['size'])}) vs ${B['price']:.2f} ({sz(B['size'])}) today. Price per ounce, key notes and which to buy."],160),body,
      [prod_ld(A, name=f"{fa} {sz(A['size'])}", brand=canon(A['brand'])),prod_ld(B, name=f"{fb} {sz(B['size'])}", brand=canon(B['brand'])),faqld(qs)])
    VS_PAGES.append((vs_rel, v))
# ---------- holiday gift guides (/gifts/...) ----------
def _sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(1<<16), b""):
            h.update(chunk)
    return h.hexdigest()
def _snapshot_media(root):
    found={}
    if not root or not os.path.isdir(root): return found
    for dirpath,_,files in os.walk(root):
        for fn in files:
            fp=os.path.join(dirpath,fn)
            rel=os.path.relpath(fp,root).replace(os.sep,"/")
            found[rel]=_sha256_file(fp)
    return found
_MEDIA_BEFORE=_snapshot_media(f"{_media_tmp}/media" if _media_tmp else "")
_GIFT_PINS_WRITTEN=set()
def write_gift_pin(slug, title):
    """One 1000x1500 pin for this guide. Never replaces the five legacy pins."""
    fn=f"{slug}.png"
    if fn in giftpins.LEGACY:
        raise SystemExit(f"gift pin {fn} would replace a legacy pin")
    root=f"{_media_tmp}/media/pins" if _media_tmp else f"{OUT}/media/pins"
    os.makedirs(root, exist_ok=True)
    template=os.path.join(root,"holiday-fragrance-gifts.png")
    if not os.path.isfile(template):
        raise SystemExit(f"pin template missing: {template}")
    giftpins.render(os.path.join(root,fn), template, slug, title, site_host=CUSTOM_DOMAIN)
    _GIFT_PINS_WRITTEN.add(f"pins/{fn}")
    return f"/media/pins/{fn}"
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
    if d.get("kind")=="mini": return False
    if d.get("kind")=="set": return True
    blob=gift_blob(d)
    if any(s in blob for s in ("gift set","gift-set","coffret","discovery set","mini set")): return True
    return bool(re.search(r"\b\d+\s*-?\s*(pc|piece|pcs)\b", blob) and "set" in blob)
def is_mini_or_travel(d):
    """Travel spray, mini, or rollerball from about 0.3 oz through 1.0 oz. A 1.7 oz bottle is not one."""
    if is_gift_set(d): return False
    if d.get("kind")=="mini": return True
    blob=gift_blob(d)
    o=oz(d.get("size") or "")
    named=bool(re.search(r"\b(mini|minis|miniature|travel(?:\s*|-)?size|travelsize|roller-?ball)\b", blob))
    if o is not None:
        return 0.3<=o<=1.0
    return named
def gift_line(d):
    """One plain line from concentration, size, and who it is for. No scent claims."""
    who={"men":"for men","women":"for women","unisex":"for men and women"}.get(d.get("gender"),"")
    bits=[b for b in (conc_name(d.get("type")), sz(d.get("size") or ""), who) if b]
    return ", ".join(bits)+"." if bits else "Price checked at an authorized retailer."
def gift_detail(d):
    if d.get("contents"):
        return str(d["contents"]).strip().rstrip(".")+"."
    return gift_line(d)
def brand_link(d):
    b=canon(d["brand"])
    if b in brands:
        return f"<a href='{PREFIX}/brands/{bslug(b)}/'>{e(b)}</a>"
    return e(b)
def fragrance_href(d):
    """Deal page only when that page is the same bottle size. A 1 oz row must not point at a 3.4 oz deal."""
    s=slug(d["brand"]+" "+d["name"])
    match=next((x for x in deals if slug(x["brand"]+" "+x["name"])==s), None)
    if not match: return None
    mo, do=oz(match.get("size")), oz(d.get("size"))
    if mo and do and abs(mo-do)>0.05: return None
    return f"{PREFIX}/fragrance/{s}/"
def gift_card(d, notes=None):
    """Roundup card markup, plus the set contents line gift guides already show."""
    notes=notes or {}
    href=fragrance_href(d)
    name=e(d["name"])
    title=f"<a href='{href}'>{name}</a>" if href else name
    size=sz(d.get("size") or "")
    size_bit=f" · {e(size)}" if size else ""
    was=""
    if isinstance(d.get("was"), (int, float)) and not isinstance(d.get("was"), bool) and d["was"]>d["price"]:
        was=f'<span class="was">${d["was"]:.2f}</span>'
    badge=f'<div><span class="badge">-{d["pct_off"]}%</span></div>' if d.get("pct_off") else ""
    label=(f"<div class=meta>compare-at price at {e(d['was_label'])}</div>" if d.get("was_label") else "")
    note=(f"<div class=meta>{e(notes[d['id']])}</div>" if d.get("id") in notes else "")
    return f"""<article class="card">{card_img(d)}
{badge}<div class="brand">{brand_link(d)}</div><div class="nm">{title}{size_bit}</div>
<div class="meta">{e(gift_detail(d))}</div>{note}
<div><span class="price">${d['price']:.2f}</span>{was}</div>
{label}<div class="meta">at {e(d['retailer'])} · checked {upd_h}</div>
{also_line(d)}
{ext_a(d['url'], f"Buy at {e(d['retailer'])}", cls="btn", placement="grid")}</article>"""
def gift_table(ds, notes=None):
    notes=notes or {}
    if not ds: return ""
    return "<div class='grid'>"+"".join(gift_card(d, notes) for d in ds)+"</div>"
def gift_sections(ds):
    groups={}; order=[]
    for d in sorted(ds, key=lambda d:(canon(d["brand"]).lower(), d["price"], d["id"])):
        b=canon(d["brand"])
        if b not in groups:
            groups[b]=[]; order.append(b)
        groups[b].append(d)
    parts=[]
    for b in order:
        heading=f"<a href='{PREFIX}/brands/{bslug(b)}/'>{e(b)}</a>" if b in brands else e(b)
        parts.append(f"<h2>{heading}</h2>"+gift_table(groups[b]))
    return "".join(parts)
def brand_chips(rows):
    seen=[]
    for d in rows:
        b=canon(d["brand"])
        if b in brands and b not in seen: seen.append(b)
    if not seen: return ""
    return "<p class='chips'>"+"".join(f"<a href='{PREFIX}/brands/{bslug(b)}/'>{e(b)} deals</a>" for b in seen)+"</p>"
GIFT_LINKS=[("","Holiday gifts"),("for-him","For him"),("for-her","For her"),("under-50","Under $50"),("gift-sets","Gift sets")]+SEO_GIFTS
BF_PATH="/black-friday-fragrance-deals/"
def gift_nav():
    """Gift-page chips, plus the Black Friday page. The site header does not link it."""
    chips="".join(f"<a href='{PREFIX}/gifts/{slug+'/' if slug else ''}'>{e(label)}</a>" for slug,label in GIFT_LINKS)
    chips+=f"<a href='{PREFIX}{BF_PATH}'>{e('Black Friday & Cyber Monday')}</a>"
    return f"<p class='chips'>{chips}</p>"
# Guides that list checked bottles. Empty pages point here instead of at each other.
FILLED_GIFT_SLUGS={"","for-him","for-her","under-50","perfume-gifts-for-her-under-50","best-mens-cologne-under-40"} | {g["slug"] for g in GIFT_GUIDES if g["picks"]}
def check_back_note(sentence):
    """Calm empty state. No table, no invented price, links only to guides that have bottles."""
    links="".join(f"<a href='{PREFIX}/gifts/{slug+'/' if slug else ''}'>{e(label)}</a>" for slug,label in GIFT_LINKS if slug in FILLED_GIFT_SLUGS)
    return f"<div class='box'><h2 style='margin-top:0'>Check back soon</h2><p>{e(sentence)}</p><p class='chips'>{links}</p></div>"
GIFT_DISC="<p>Affiliate disclosure: some links on this page earn us a commission if you buy, at no extra cost to you. Prices are the ones we checked at authorized retailers.</p>"
eligible=[d for d in deals if gift_ok(d)]
by_off=sorted(eligible, key=lambda d:(-(d.get("pct_off") or 0), d["price"], d["id"]))
gift_pages=[
 ("gifts/index.html","","Holiday fragrance gifts","Fragrance gifts from checked deals",
  "Single bottles on sale now, for November and December. Largest checked discount first.",
  by_off[:12],"Holiday fragrance gifts"),
 ("gifts/for-him/index.html","for-him","Fragrance gifts for him","Men's cologne gifts",
  "Men's colognes from today's checked deals, largest discount first.",
  [d for d in by_off if d["gender"]=="men"][:12],"Fragrance gifts for him"),
 ("gifts/for-her/index.html","for-her","Fragrance gifts for her","Women's perfume gifts",
  "Women's perfumes from today's checked deals, largest discount first.",
  [d for d in by_off if d["gender"]=="women"][:12],"Fragrance gifts for her"),
 ("gifts/under-50/index.html","under-50","Fragrance gifts under $50","Gifts under $50",
  "The lowest prices we checked that are still under $50.",
  sorted([d for d in eligible if d["price"]<50], key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))[:12],"Fragrance gifts under $50"),
]
for path,sid_slug,title,short,intro,picks,list_name in gift_pages:
    image=write_gift_pin(sid_slug or "gifts", title)
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
        desc="Check back soon. No boxed fragrance gift set is in today's checked deals. Single bottles are on the other gift guides."
        listing=check_back_note("No boxed fragrance gift set is in today's checked deals, so this page has no list. These guides have bottles we priced.")
        ld=None
        titles=fit([f"{title} ({upd:%b %Y}) | {NAME}", f"{title} | {NAME}", title])
    hub_extra=""
    top_mark=""
    bot_mark=""
    if path=="gifts/index.html":
        hub_extra=f"<p>For the long weekend, <a href='{PREFIX}{BF_PATH}'>Black Friday and Cyber Monday fragrance deals</a> rebuilds from the same daily price check.</p>"
        top_mark=GIFT_HUB_MARK
    else:
        register_gift_subpage(sid_slug, title)
        GIFT_PAGE_PICKS.append((sid_slug, title, list(picks)))
        bot_mark=GIFT_MORE_MARK
    page(path, titles,
      desc,
      f"<h1>{e(title)}</h1><p class='sub'>{e(intro)} Checked {upd_h}.</p>{gift_nav()}{hub_extra}{top_mark}{GIFT_DISC}{listing}{bot_mark}<p class='meta'>Each name links to that bottle's price comparison. We do not list testers, decants, or Amazon.</p>",
      ld, image=image, feed=bool(picks))
    extra=short.lower()
    KW+=[title.lower(), extra if "fragrance" in extra else f"fragrance {extra}"]
def by_price(rows):
    return sorted(rows, key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))
def lowest_deal(rows):
    return min(rows, key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"]))
def seo_title(h1, picks):
    if not picks: return fit([f"{h1} | {NAME}", h1])
    price=f"${lowest_deal(picks)['price']:.2f}"
    return fit([f"{h1}: From {price} | {NAME}", f"{h1}: From {price}", h1])
def seo_meta_filled(n_label, picks, tail="Sealed bottles only."):
    lo=lowest_deal(picks)
    price=f"${lo['price']:.2f}"
    when=f"{upd:%b %-d, %Y}"
    size_bit=f" ({sz(lo['size'])})" if lo.get("size") and not lo.get("contents") else ""
    off=max((d.get("pct_off") or 0) for d in picks)
    off_bit=f" Up to {off}% off." if off else ""
    who=f"{fullname(lo)}{size_bit} at {lo['retailer']}"
    return fit([
        f"{len(picks)} {n_label}, starting at {price} for {who}.{off_bit} Checked {when}. {tail}",
        f"{len(picks)} {n_label}, starting at {price} for {who}.{off_bit} Checked {when}.",
        f"{len(picks)} {n_label}, starting at {price} for {who}. Checked {when}. {tail}",
        f"{len(picks)} {n_label}, starting at {price} for {who}. Checked {when}.",
        f"{len(picks)} {n_label}, starting at {price} at {lo['retailer']}. Checked {when}.",
    ],160)
def render_seo_gift(slug_s, h1, intro, picks, faqs, empty_html, empty_desc, filled_label, notes=None, extra_html="", extra="", group_by_brand=False, tail="Sealed bottles only."):
    use_sid("gifts", slug_s)
    image=write_gift_pin(slug_s, h1)
    register_gift_subpage(slug_s, h1)
    GIFT_PAGE_PICKS.append((slug_s, h1, list(picks or [])))
    title=seo_title(h1, picks)
    desc=seo_meta_filled(filled_label, picks, tail) if picks else empty_desc
    if picks:
        listing=(gift_sections(picks) if group_by_brand else gift_table(picks, notes))+brand_chips(picks)
    else:
        listing=empty_html
    ld=([itemlist(picks, h1)] if picks else [])+[faqld(faqs)]
    page(f"gifts/{slug_s}/index.html", title, desc,
      f"<h1>{e(h1)}</h1><p class='sub'>{e(intro)} Checked {upd_h}.</p>{gift_nav()}{GIFT_DISC}{extra}{listing}{faqhtml(faqs)}{extra_html}{BREVO_FORM}{GIFT_MORE_MARK}<p class='meta'>Prices are the ones we checked. A name links to a price comparison only when that same size already has a deal page. We do not invent a price, and we do not list testers, decants, or Amazon.</p>",
      ld, image=image, feed=bool(picks))
    KW.append(h1.lower())
her_under_50=by_price([d for d in eligible if d["gender"]=="women" and d["price"]<50])
men_under_40=by_price([d for d in eligible if d["gender"]=="men" and d["price"]<40])
catalog=[d for d in (D.get("gifts") or []) if gift_ok(d)]
catalog_ids={d["id"] for d in catalog}
travel=[d for d in catalog if d.get("kind")=="mini"]
travel+=[d for d in eligible if d["id"] not in catalog_ids and is_mini_or_travel(d)]
boxed=[d for d in catalog if d.get("kind")=="set"]
boxed+=[d for d in eligible if d["id"] not in catalog_ids and is_gift_set(d)]
mini_picks=by_price(travel)[:12]
holiday_picks=by_price([d for d in boxed if d["price"]<75])[:12]
brand_picks=by_price([d for d in boxed if d["price"]>=75])[:12]
if mini_picks: FILLED_GIFT_SLUGS.add("stocking-stuffer-minis")
if holiday_picks: FILLED_GIFT_SLUGS.add("holiday-gift-sets")
if brand_picks: FILLED_GIFT_SLUGS.add("gift-sets")
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
mini_lo=lowest_deal(mini_picks) if mini_picks else None
holiday_lo=lowest_deal(holiday_picks) if holiday_picks else None
brand_lo=lowest_deal(brand_picks) if brand_picks else None
roller_on_page=any(re.search(r"roller", gift_blob(d)) for d in mini_picks)
roller_line=(" This page includes a rollerball we checked." if roller_on_page else " No in-stock rollerball turned up in the catalog we checked, so the rows are travel sprays.")
render_seo_gift("stocking-stuffer-minis","Fragrance minis and travel sizes",
  "Travel sprays and minis from 0.3 oz to 1.0 oz for a stocking, lowest price first. A 1.7 oz bottle stays on the other gift guides.",
  mini_picks,([
    ("What counts as a stocking stuffer here?",
     "A travel spray, mini, or rollerball from about 0.3 oz to 1.0 oz, priced at Perfumania or FragranceShop. Bottles of 1.7 oz and larger stay on the other gift guides."+roller_line),
    ("What is the lowest travel size you checked?",
     f"{fullname(mini_lo)} is ${mini_lo['price']:.2f} for {sz(mini_lo['size'])} at {mini_lo['retailer']}. {len(mini_picks)} travel sizes are on this page, from ${mini_lo['price']:.2f} to ${max(d['price'] for d in mini_picks):.2f}."),
    ("Are these prices estimated?",
     f"No. Each price is the price we checked at that row's retailer. Checked {upd_h}."),
  ] if mini_picks else [
    ("Are there fragrance minis or travel sizes today?",
     "Not in the products we checked. Nothing in stock is a 0.3 to 1.0 oz travel spray, mini, or rollerball."),
    ("Is a 1.7 oz bottle a stocking stuffer here?",
     "No. This page is 0.3 oz to 1.0 oz. Larger bottles stay on the perfume and cologne gift guides."),
    ("Where should I look instead?",
     "Holiday gift sets and the gift sets by brand list boxed sets we did price."),
  ]),
  check_back_note("No fragrance mini or travel size is in the products we checked, so this page has no list. A 1.7 oz bottle stays on the other guides. These guides have products we priced."),
  "Check back soon. No 0.3 to 1.0 oz fragrance mini or travel spray is in the products we checked.",
  "fragrance minis and travel sizes",
  extra="<p>Boxed coffrets under $75 are on <a href='/gifts/holiday-gift-sets/'>holiday gift sets</a>. Sets at $75 and up are grouped by brand on <a href='/gifts/gift-sets/'>gift sets</a>.</p>")
render_seo_gift("holiday-gift-sets","Holiday fragrance gift sets",
  "Boxed sets we checked under $75: miniature coffrets and other multi-piece sets. Lowest price first. A single bottle is not listed as a set.",
  holiday_picks,([
    ("Which holiday gift set is the lowest price?",
     f"The lowest set on this page is ${holiday_lo['price']:.2f} for {fullname(holiday_lo)} at {holiday_lo['retailer']}. {len(holiday_picks)} sets here are under $75, up to ${max(d['price'] for d in holiday_picks):.2f}."),
    ("Why isn't every gift set on this page?",
     "This page is seasonal coffrets and other boxed sets under $75. Sets at $75 and up are grouped by brand on the gift sets page. The two lists do not share a product."),
    ("Do you guess a set price?",
     f"No. A set is listed only after we check its price and that the retailer calls it a set. Checked {upd_h}."),
  ] if holiday_picks else [
    ("Do you have fragrance gift sets under $75?",
     "Not today. None of the boxed sets we checked is under $75."),
    ("Will you guess a set price?",
     "No. A set is listed only after we check its price and that it is in stock."),
    ("Where are the other sets?",
     "Sets at $75 and up are on the gift sets page, grouped by brand. Single bottles are on the other gift guides."),
  ]),
  check_back_note("No fragrance gift set under $75 is in the products we checked, so this page has no list. These guides have products we priced."),
  "Check back soon. No fragrance gift set under $75 is in the products we checked.",
  "boxed fragrance sets under $75",
  extra="<p>Sets at $75 and up, grouped by brand, are on <a href='/gifts/gift-sets/'>gift sets</a>. Travel sprays are on <a href='/gifts/stocking-stuffer-minis/'>stocking stuffer minis</a>.</p>",
  tail="Boxed sets only.")
render_seo_gift("gift-sets","Designer fragrance gift sets",
  "Boxed sets at $75 and up, grouped by brand. A single bottle is not listed as a set.",
  brand_picks,([
    ("How is this different from holiday gift sets?",
     "Holiday gift sets are the boxed sets we checked under $75. This page lists sets at $75 and up and groups them by brand. The same set is not on both pages."),
    ("Which set on this page costs the least?",
     f"The lowest set here is ${brand_lo['price']:.2f} for {fullname(brand_lo)} at {brand_lo['retailer']}. {len(brand_picks)} sets are listed, up to ${max(d['price'] for d in brand_picks):.2f}."),
    ("Are single bottles included?",
     f"No. Each row is a multi-piece set the retailer sells as a gift set. Checked {upd_h}."),
  ] if brand_picks else [
    ("Do you have fragrance gift sets at $75 and up?",
     "Not today. None of the boxed sets we checked is $75 or more."),
    ("Where are the sets under $75?",
     "On the holiday gift sets page."),
    ("Will you guess a set price?",
     "No. A set is listed only after we check its price and that it is in stock."),
  ]),
  check_back_note("No fragrance gift set at $75 or more is in the products we checked, so this page has no list. These guides have products we priced."),
  "Check back soon. No fragrance gift set at $75 or more is in the products we checked.",
  "boxed fragrance sets at $75 and up",
  extra="<p>Coffrets under $75 are on <a href='/gifts/holiday-gift-sets/'>holiday gift sets</a>. Travel sprays are on <a href='/gifts/stocking-stuffer-minis/'>stocking stuffer minis</a>.</p>",
  group_by_brand=True, tail="Boxed sets only.")
for spec in GIFT_GUIDES:
    picks=spec["picks"]
    h1=spec["title"]
    cap=spec.get("max_price")
    floor=spec.get("min_was")
    bits=[spec["intro"]]
    if isinstance(cap,(int,float)) and not isinstance(cap,bool):
        if spec.get("max_price_inclusive"):
            bits.append(f"Price cap: ${cap:g} or less. A checked price above ${cap:g} is left off on the next rebuild.")
        else:
            bits.append(f"Price cap: under ${cap:g}. A checked price of ${cap:g} or more is left off on the next rebuild.")
    floor_price=spec.get("min_price")
    if isinstance(floor_price,(int,float)) and not isinstance(floor_price,bool):
        bits.append(f"Price floor: ${floor_price:g} or more. A checked price under ${floor_price:g} stays on the lower-budget guide.")
    if isinstance(floor,(int,float)) and not isinstance(floor,bool):
        bits.append(f"Included only when the checked compare-at price is ${floor:g} or higher.")
    noted=[(d, NOTE_BY_ID[d["id"]]) for d in picks if d["id"] in NOTE_BY_ID]
    if noted:
        sample=noted[:3]
        bits.append("Retailer note lines include "+"; ".join(f"{fullname(d)} ({n})" for d,n in sample)+".")
    intro=" ".join(bits)
    notes={d["id"]: NOTE_BY_ID[d["id"]] for d in picks if d["id"] in NOTE_BY_ID}
    faqs=[]
    if picks:
        lo=lowest_deal(picks)
        faqs.append((f"What is the lowest price for {h1.lower()}?",
            f"The lowest price we checked is ${lo['price']:.2f} for {fullname(lo)} ({sz(lo['size'])}) at {lo['retailer']}. {len(picks)} bottles are on this page. Checked {upd_h}."))
        faqs.append(("Are these prices estimated?",
            f"No. Every price is copied from a deal we checked. Checked {upd_h}. We do not invent a price."))
        faqs.append(("Do you list testers, decants, or Amazon?",
            "No. These are sealed bottles at Perfumania or FragranceShop. Testers, decants, and Amazon are left out."))
    else:
        faqs.append((f"Do you have {h1.lower()} today?",
            "Not in the deals we checked. This page stays up so the address does not disappear, and it fills in when a matching bottle is on sale."))
        faqs.append(("Will you estimate a price?",
            "No. A bottle is listed only after we check its price."))
    for pair in spec.get("faq") or []:
        faqs.append((pair[0], pair[1]))
    extra=""
    if spec.get("links"):
        extra="<p class='chips'>"+"".join(f"<a href='{PREFIX}{l['href']}'>{e(l['label'])}</a>" for l in spec["links"])+"</p>"
    render_seo_gift(spec["slug"], h1, intro, picks, faqs,
        check_back_note(spec["empty"]), spec["empty_desc"], spec["filled_label"], notes=notes, extra_html=extra)
def gift_guide_section(heading, pairs, extra=()):
    """Labeled chip block. Anchor text is the guide's page title (its h1)."""
    links="".join(f"<a href='{PREFIX}/gifts/{slug}/'>{e(title)}</a>" for slug, title in pairs)
    links+="".join(f"<a href='{href}'>{e(label)}</a>" for href, label in extra)
    return f"<section class='box'><h2 style='margin-top:0'>{e(heading)}</h2><div class='chips'>{links}</div></section>"
def _page_h1(rel):
    text=open(f"{OUT}/{rel}", encoding="utf-8").read()
    m=re.search(r"<h1>(.*?)</h1>", text, re.S)
    if not m: raise SystemExit(f"{rel}: no h1")
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
def _splice_mark(rel, mark, html_block):
    fp=f"{OUT}/{rel}"
    text=open(fp, encoding="utf-8").read()
    n=text.count(mark)
    if n!=1: raise SystemExit(f"{rel}: expected one {mark}, found {n}")
    open(fp,"w", encoding="utf-8").write(text.replace(mark, html_block, 1))
def _section_anchors(rel, heading):
    text=open(f"{OUT}/{rel}", encoding="utf-8").read()
    m=re.search(rf"<section class='box'><h2 style='margin-top:0'>{re.escape(e(heading))}</h2><div class='chips'>(.*?)</div></section>", text, re.S)
    if not m: raise SystemExit(f"{rel}: missing {heading} section")
    return [(html.unescape(href), html.unescape(label)) for href, label in re.findall(r"<a href='([^']*)'>(.*?)</a>", m.group(1), re.S)]
def _price_under(d, cap):
    p=d.get("price")
    return isinstance(p,(int,float)) and not isinstance(p,bool) and p<cap
def general_gift_guides(ds, by_slug, picks_by):
    """3 or 4 broad for-him / for-her / under-$50 guides.

    Used only when none of this brand's deals is on a gift page. Titles are the
    pages this build registered. A guide with no bottles is skipped.
    """
    genders={d.get("gender") for d in ds}
    has_men="men" in genders
    has_women="women" in genders
    unisex_only=not has_men and not has_women
    order=[]
    def add(slug):
        if slug in order or slug not in by_slug: return False
        if not picks_by.get(slug): return False
        order.append(slug)
        return True
    if has_men or unisex_only: add("for-him")
    if has_women or unisex_only: add("for-her")
    add("under-50")
    if has_men and has_women:
        men_n=sum(1 for d in ds if d.get("gender")=="men" and _price_under(d, 50))
        women_n=sum(1 for d in ds if d.get("gender")=="women" and _price_under(d, 50))
        add("perfume-gifts-for-her-under-50" if women_n>men_n else "cologne-gifts-for-him-under-50")
    elif has_men:
        add("cologne-gifts-for-him-under-50")
        if any(d.get("gender")=="men" and _price_under(d, 40) for d in ds):
            add("best-mens-cologne-under-40")
    elif has_women:
        add("perfume-gifts-for-her-under-50")
        if any(d.get("gender")=="women" and _price_under(d, 40) for d in ds):
            add("perfume-gifts-for-her-under-40")
    fillers=("for-him","for-her","under-50","cologne-gifts-for-him-under-50",
             "perfume-gifts-for-her-under-50","best-mens-cologne-under-40","perfume-gifts-for-her-under-40")
    for slug in fillers:
        if len(order)>=3: break
        add(slug)
    if len(order)>4: order=order[:4]
    if not (3<=len(order)<=4):
        raise SystemExit("general gift guides: expected 3 or 4 available guides, got "+", ".join(order) or "(none)")
    return [(slug, by_slug[slug]) for slug in order]
def _deal_key(d):
    """Identity of a checked deal. Gift-catalog rows can reuse a retailer handle as id for a different size."""
    price=d.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)): price=None
    return (d.get("id"), sz(d.get("size") or ""), price)
def _guides_featuring(brand_deals):
    """Gift pages whose rendered list includes at least one of this brand's deals."""
    keys={_deal_key(d) for d in brand_deals}
    found=[]
    for slug, title, picks in GIFT_PAGE_PICKS:
        if any(_deal_key(p) in keys for p in picks):
            found.append((slug, title))
    return found
def apply_brand_gift_guides():
    """Splice 'Gift guides featuring <Brand>' onto each brand page from the gift-page picks."""
    registered=[slug for slug,_ in GIFT_SUBPAGES]
    recorded=[slug for slug,_,_ in GIFT_PAGE_PICKS]
    if recorded!=registered:
        raise SystemExit("brand gift guides: recorded pages drifted from registered gift guides")
    by_slug=dict(GIFT_SUBPAGES)
    for slug, title, _picks in GIFT_PAGE_PICKS:
        if by_slug[slug]!=title:
            raise SystemExit(f"brand gift guides: {slug} title {title!r} != registered {by_slug[slug]!r}")
        if _page_h1(f"gifts/{slug}/index.html")!=title:
            raise SystemExit(f"brand gift guides: {slug} title is not the page h1")
    picks_by={slug: picks for slug, _title, picks in GIFT_PAGE_PICKS}
    for b in brands:
        ds=[d for d in deals if canon(d["brand"])==b]
        featured=_guides_featuring(ds)
        mode="featured"
        if not featured:
            pairs=general_gift_guides(ds, by_slug, picks_by)
            mode="fallback"
        elif len(featured)<2:
            pairs=list(featured)
            for slug, title in general_gift_guides(ds, by_slug, picks_by):
                if slug not in {s for s,_ in pairs}:
                    pairs.append((slug, title))
                    break
            mode="topup"
        else:
            pairs=featured
        if len(pairs)<2:
            raise SystemExit(f"{b}: brand page has {len(pairs)} gift-guide links")
        if mode=="fallback" and not (3<=len(pairs)<=4):
            raise SystemExit(f"{b}: fallback linked {len(pairs)} guides, expected 3 or 4")
        featured_slugs={s for s,_ in featured}
        linked_slugs={s for s,_ in pairs}
        if mode!="fallback" and not featured_slugs<=linked_slugs:
            raise SystemExit(f"{b}: dropped a gift guide that includes this brand's deals")
        if mode=="featured" and linked_slugs!=featured_slugs:
            raise SystemExit(f"{b}: linked a gift guide that does not include this brand's deals")
        heading=f"Gift guides featuring {b}"
        rel=f"brands/{bslug(b)}/index.html"
        _splice_mark(rel, BRAND_GIFT_MARK, gift_guide_section(heading, pairs))
        got=_section_anchors(rel, heading)
        expect=[(f"{PREFIX}/gifts/{slug}/", title) for slug, title in pairs]
        if got!=expect:
            raise SystemExit(f"{b}: gift guide section links drifted")
        for href, label in got:
            slug=href[len(f"{PREFIX}/gifts/"):].strip("/")
            if slug not in by_slug:
                raise SystemExit(f"{b}: {href} is not a gift guide page")
            if not os.path.isfile(f"{OUT}/gifts/{slug}/index.html"):
                raise SystemExit(f"{b}: {href} was not built")
            if label!=by_slug[slug]:
                raise SystemExit(f"{b}: anchor {label!r} is not the gift guide title")
        print(f"brand gift guides: {b} -> {len(pairs)} ({mode}): {', '.join(s for s,_ in pairs)}")
    hub_rel="brands/index.html"
    hub=open(f"{OUT}/{hub_rel}", encoding="utf-8").read()
    if BRAND_GIFT_MARK in hub or "Gift guides featuring" in hub:
        raise SystemExit("brands hub should not list per-brand gift guides")
    brand_rels=[]
    for dirpath, _, files in os.walk(f"{OUT}/brands"):
        for fn in files:
            if fn.endswith(".html"):
                brand_rels.append(os.path.relpath(os.path.join(dirpath, fn), OUT).replace(os.sep, "/"))
    pages=[r for r in brand_rels if r!="brands/index.html"]
    if len(pages)!=len(brands):
        raise SystemExit(f"brand gift guides: {len(pages)} brand pages for {len(brands)} brands")
    for rel in pages:
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if BRAND_GIFT_MARK in text:
            raise SystemExit(f"{rel}: still contains {BRAND_GIFT_MARK}")
        if text.count("Gift guides featuring ")!=1:
            raise SystemExit(f"{rel}: expected one Gift guides featuring section")
_OCCASION_GIFT_SLUGS={
    "fragrance-gifts-for-teens","secret-santa-fragrances-under-30",
    "stocking-stuffer-fragrances","fragrance-stocking-stuffers-under-25",
}
_GIFT_HUB_SLUGS={"for-him","for-her"}
def dupe_price(d):
    p=d.get("price")
    if isinstance(p, bool) or not isinstance(p, (int, float)): return None
    return p
def _gift_rule_rows():
    """Guides a dupe page may link. Roundup-gated and compare-at guides stay out of the first pass."""
    rows=[]; seen=set()
    static=[
        ("for-him","men",None,None,False,False,False),
        ("for-her","women",None,None,False,False,False),
        ("under-50",None,50,None,False,False,False),
        ("perfume-gifts-for-her-under-50","women",50,None,False,False,False),
        ("best-mens-cologne-under-40","men",40,None,False,False,False),
    ]
    def add(slug, gender, max_price, min_price, inclusive, roundup, occasion, prefer=0):
        if slug in seen: return
        seen.add(slug)
        rows.append({"slug":slug,"gender":gender,"max_price":max_price,"min_price":min_price,
                     "inclusive":bool(inclusive),"roundup":bool(roundup),
                     "occasion":bool(occasion) or slug in _OCCASION_GIFT_SLUGS,"prefer":prefer})
    for row in static: add(*row)
    for spec in GIFT_GUIDES:
        if spec.get("min_was"): continue
        add(spec["slug"], spec.get("gender"), spec.get("max_price"), spec.get("min_price"),
            spec.get("max_price_inclusive"), spec.get("roundups"), spec.get("include_travel"),
            1 if spec.get("include_travel") else 0)
    return rows
def _price_fits(price, rule, allow_missing):
    max_price, min_price=rule.get("max_price"), rule.get("min_price")
    if max_price is None and min_price is None: return True
    if price is None: return allow_missing
    if max_price is not None:
        if rule.get("inclusive"):
            if price>max_price: return False
        elif price>=max_price: return False
    if min_price is not None and price<min_price: return False
    return True
def _audience_fits(aud, rule):
    gender=rule.get("gender")
    if not gender: return True
    if aud==gender: return True
    if aud=="unisex" and rule["slug"] in _GIFT_HUB_SLUGS: return True
    return False
def gift_links_for_dupe(d, by_slug):
    """2–4 gift guides. Gender from the dupe record; a price cap only when today's price is under it."""
    aud, price=dupe_audience(d), dupe_price(d)
    filled={slug for slug, _title, picks in GIFT_PAGE_PICKS if picks}
    rules=[r for r in _gift_rule_rows() if r["slug"] in by_slug and r["slug"] in filled and _audience_fits(aud, r)]
    def ok(r, allow_missing=False):
        return _price_fits(price, r, allow_missing)
    hubs=[r for r in rules if r["slug"] in _GIFT_HUB_SLUGS and ok(r)]
    gender_caps=sorted([r for r in rules if r["gender"] and r["max_price"] is not None and not r["roundup"] and ok(r)],
                       key=lambda r:(r["max_price"], r["slug"]))
    ungendered=sorted([r for r in rules if not r["gender"] and r["max_price"] is not None and not r["roundup"] and not r["occasion"] and ok(r)],
                      key=lambda r:(r["max_price"], r["slug"]))
    occasion=sorted([r for r in rules if r["occasion"] and not r["roundup"] and r["max_price"] is not None and ok(r)],
                    key=lambda r:(r["max_price"], r["prefer"], r["slug"]))
    floors=sorted([r for r in rules if r["gender"] and r["min_price"] is not None and not r["roundup"] and ok(r)],
                  key=lambda r:(-(r["min_price"] or 0), r["slug"]))
    chosen=[]
    def take(group):
        for r in group:
            if len(chosen)>=4: return
            if r["slug"] in chosen: continue
            chosen.append(r["slug"])
    take(hubs)
    take(gender_caps)
    tight=min((r["max_price"] for r in gender_caps), default=None)
    # A $25 or $30 guide is the matching under-$X page. The under-$40 teen list is only a filler
    # when the page would otherwise have a single link (no gender on the dupe record).
    if occasion and (tight is None or occasion[0]["max_price"]<tight):
        if occasion[0]["max_price"]<=30 or len(chosen)<2:
            take(occasion[:1])
    take(ungendered[:1])
    take(floors)
    if len(chosen)<2:
        fillers=sorted([r for r in rules if r["roundup"] and ok(r, price is None)],
                       key=lambda r:(r["max_price"] if r["max_price"] is not None else 10**9, r["slug"]))
        take(fillers)
    if not 2<=len(chosen)<=4:
        raise SystemExit(f"dupe gift guides for {d.get('dupe')}: expected 2–4, got {chosen} (audience={aud}, price={price})")
    return [(slug, by_slug[slug]) for slug in chosen]
def apply_dupe_gift_guides():
    """Splice gift-guide chips onto each dupe page from guides this build registered."""
    by_slug=dict(GIFT_SUBPAGES)
    if len(DUPE_PAGES)!=len(D["dupes"]):
        raise SystemExit(f"dupe pages recorded {len(DUPE_PAGES)} for {len(D['dupes'])} dupes")
    for rel, d in DUPE_PAGES:
        pairs=gift_links_for_dupe(d, by_slug)
        _splice_mark(rel, DUPE_GIFT_MARK, gift_guide_section("Gift guides", pairs))
        got=_section_anchors(rel, "Gift guides")
        expect=[(f"{PREFIX}/gifts/{slug}/", title) for slug, title in pairs]
        if got!=expect:
            raise SystemExit(f"{rel}: gift guide section drifted")
        print(f"dupe gift guides: {d['dupe']} ({dupe_audience(d) or 'unspecified'}, {('$' + format(dupe_price(d), '.2f')) if dupe_price(d) is not None else 'no price'}) -> {', '.join(s for s,_ in pairs)}")
FRAGRANCE_GIFT_HEADING="Featured in these gift guides"
FRAGRANCE_GIFT_LINKS=[]
# Audience and price filters for the gift pages that are not config specs.
# These are the same filters the page builders use. Not a list of products.
_STRUCTURAL_GIFT_RULES=(
    {"slug":"for-him","gender":"men"},
    {"slug":"for-her","gender":"women"},
    {"slug":"under-50","max_price":50},
    {"slug":"perfume-gifts-for-her-under-50","gender":"women","max_price":50},
    {"slug":"best-mens-cologne-under-40","gender":"men","max_price":40},
)
def fragrance_gift_section(heading, pairs, extra=()):
    """Chip block. hrefs are double-quoted so they match the rest of the page chrome."""
    def anchor(href, label):
        return f'<a href="{e(href)}">{e(label)}</a>'
    links="".join(anchor(f"{PREFIX}/gifts/{slug}/", title) for slug, title in pairs)
    links+="".join(anchor(href, label) for href, label in extra)
    return f"<section class='box'><h2 style='margin-top:0'>{e(heading)}</h2><div class='chips'>{links}</div></section>"
def _chip_anchors(blob):
    out=[]
    for m in re.finditer(r"<a href=(?:\"([^\"]*)\"|'([^']*)')>(.*?)</a>", blob, re.S):
        href=m.group(1) if m.group(1) is not None else m.group(2)
        label=re.sub(r"<[^>]+>", "", m.group(3))
        out.append((html.unescape(href), html.unescape(label)))
    return out
def _section_chip_anchors(rel, heading):
    text=open(f"{OUT}/{rel}", encoding="utf-8").read()
    m=re.search(rf"<section class='box'><h2 style='margin-top:0'>{re.escape(e(heading))}</h2><div class='chips'>(.*?)</div></section>", text, re.S)
    if not m: raise SystemExit(f"{rel}: missing {heading} section")
    return _chip_anchors(m.group(1))
def _pick_features_deal(pick, deal):
    """True when this rendered row is the fragrance page's bottle."""
    if _deal_key(pick)==_deal_key(deal): return True
    if slug((pick.get("brand") or "")+" "+(pick.get("name") or ""))!=slug(deal["brand"]+" "+deal["name"]):
        return False
    po, do=oz(pick.get("size")), oz(deal.get("size"))
    return bool(po and do and abs(po-do)<=0.05)
def guides_featuring_deal(deal):
    """Gift pages whose rendered list includes this bottle, in the order the pages were built."""
    found=[]
    for gslug, _title, picks in GIFT_PAGE_PICKS:
        if picks and any(_pick_features_deal(p, deal) for p in picks):
            found.append(gslug)
    return found
def _guide_rule_fits(rule, d):
    """Gender and checked price only. Roundup, compare-at, and travel-mix guides are not a fallback."""
    if rule.get("roundups") or rule.get("include_travel") or rule.get("min_was"): return False
    g=rule.get("gender")
    if g and d.get("gender")!=g: return False
    price=d.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)): return False
    cap=rule.get("max_price")
    if isinstance(cap,(int,float)) and not isinstance(cap,bool):
        if rule.get("max_price_inclusive"):
            if price>cap: return False
        elif price>=cap: return False
    floor=rule.get("min_price")
    if isinstance(floor,(int,float)) and not isinstance(floor,bool) and price<floor: return False
    return True
def _gender_price_guides(d, by_slug, picks_by):
    rules=[spec for spec in GIFT_GUIDES if spec.get("slug") in by_slug]
    rules+=[r for r in _STRUCTURAL_GIFT_RULES if r["slug"] in by_slug]
    def sort_key(rule):
        cap=rule.get("max_price")
        floor=rule.get("min_price") or 0
        gendered=0 if rule.get("gender") else 1
        cap_v=cap if isinstance(cap,(int,float)) and not isinstance(cap,bool) else 10**6
        floor_v=floor if isinstance(floor,(int,float)) and not isinstance(floor,bool) else 0
        return (gendered, cap_v, -floor_v, rule["slug"])
    seen=set(); ranked=[]
    for rule in sorted(rules, key=sort_key):
        gslug=rule["slug"]
        if gslug in seen or not picks_by.get(gslug): continue
        if not _guide_rule_fits(rule, d): continue
        seen.add(gslug)
        ranked.append((gslug, by_slug[gslug]))
    return ranked
def fragrance_fallback_pairs(d, by_slug, picks_by):
    """2 or 3 filled guides that match this bottle's gender and checked price.

    Used only when no rendered gift list contains the bottle. A short list is
    padded from the same broad guides brand pages use.
    """
    pairs=_gender_price_guides(d, by_slug, picks_by)
    if len(pairs)>3: pairs=pairs[:3]
    if len(pairs)>=2: return pairs
    for gslug, title in general_gift_guides([d], by_slug, picks_by):
        if gslug not in {s for s,_ in pairs} and picks_by.get(gslug):
            pairs.append((gslug, title))
        if len(pairs)>=3: break
    return pairs[:3]
def apply_fragrance_gift_guides():
    """Splice 'Featured in these gift guides' onto each fragrance page from the rendered gift lists."""
    global FRAGRANCE_GIFT_LINKS
    if not FRAGRANCE_PAGES:
        raise SystemExit("fragrance gift guides: no fragrance pages")
    if len(FRAGRANCE_PAGES)!=len({rel for rel,_ in FRAGRANCE_PAGES}):
        raise SystemExit("fragrance gift guides: two deals wrote the same page")
    by_slug=dict(GIFT_SUBPAGES)
    for gslug, title, _picks in GIFT_PAGE_PICKS:
        if by_slug.get(gslug)!=title:
            raise SystemExit(f"fragrance gift guides: {gslug} title {title!r} != registered {by_slug.get(gslug)!r}")
    picks_by={gslug: picks for gslug, _title, picks in GIFT_PAGE_PICKS}
    FRAGRANCE_GIFT_LINKS=[]
    counts=[]
    for rel, d in FRAGRANCE_PAGES:
        featured=[(gslug, by_slug[gslug]) for gslug in guides_featuring_deal(d)]
        if featured:
            pairs=featured
            mode="featured"
        else:
            pairs=fragrance_fallback_pairs(d, by_slug, picks_by)
            mode="fallback"
        if not pairs:
            raise SystemExit(f"{rel}: no gift guide for {d.get('id')} ({d.get('gender')}, {d.get('price')})")
        if mode=="fallback" and not (2<=len(pairs)<=3):
            raise SystemExit(f"{rel}: fallback linked {len(pairs)} guides, expected 2 or 3")
        if mode=="featured":
            want=guides_featuring_deal(d)
            if [s for s,_ in pairs]!=want:
                raise SystemExit(f"{rel}: featured guides drifted")
            for gslug, _title in pairs:
                if not any(_pick_features_deal(p, d) for p in picks_by.get(gslug) or []):
                    raise SystemExit(f"{rel}: {gslug} does not include this fragrance")
        b=canon(d["brand"])
        brand_href=f"{PREFIX}/brands/{bslug(b)}/"
        pre=open(f"{OUT}/{rel}", encoding="utf-8").read()
        extra=()
        if b in brands and brand_href not in pre:
            extra=((brand_href, f"More from {b}"),)
        _splice_mark(rel, FRAGRANCE_GIFT_MARK, fragrance_gift_section(FRAGRANCE_GIFT_HEADING, pairs, extra))
        got=_section_chip_anchors(rel, FRAGRANCE_GIFT_HEADING)
        expect=[(f"{PREFIX}/gifts/{gslug}/", title) for gslug, title in pairs]+[(href, label) for href, label in extra]
        if got!=expect:
            raise SystemExit(f"{rel}: gift guide section drifted")
        for href, label in got:
            path=_href_path(href)
            if path==brand_href:
                if label!=f"More from {b}":
                    raise SystemExit(f"{rel}: brand link label {label!r}")
                continue
            if path==f"{PREFIX}/gifts/":
                raise SystemExit(f"{rel}: gift section links the hub instead of a guide")
            gslug=path[len(f"{PREFIX}/gifts/"):].strip("/")
            if gslug not in by_slug or label!=by_slug[gslug]:
                raise SystemExit(f"{rel}: anchor {label!r} is not a built guide title")
            if not os.path.isfile(f"{OUT}/gifts/{gslug}/index.html"):
                raise SystemExit(f"{rel}: {path} was not built")
            if not picks_by.get(gslug):
                raise SystemExit(f"{rel}: {gslug} has no deals")
            if f'href="{path}"' not in open(f"{OUT}/{rel}", encoding="utf-8").read():
                raise SystemExit(f"{rel}: {path} is not a double-quoted href")
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if text.count(FRAGRANCE_GIFT_HEADING)!=1:
            raise SystemExit(f"{rel}: expected one {FRAGRANCE_GIFT_HEADING} section")
        if "<b>Holiday gift guides:</b>" in text:
            raise SystemExit(f"{rel}: old holiday gift line is still on the page")
        counts.append(len(pairs))
        FRAGRANCE_GIFT_LINKS.append((rel, list(pairs), mode))
        print(f"fragrance gift guides: {fullname(d)} -> {len(pairs)} ({mode}): {', '.join(s for s,_ in pairs)}")
    print(f"fragrance gift guides: {len(counts)} pages, min {min(counts)} max {max(counts)} specific guide links")
def audit_fragrance_gift_links():
    """Every sitemap /fragrance/ URL links to at least one specific /gifts/<guide>/ page."""
    paths=_sitemap_paths()
    frag=sorted(p for p in paths if p.startswith(f"{PREFIX}/fragrance/"))
    if not FRAGRANCE_GIFT_LINKS:
        raise SystemExit("fragrance gift guides: nothing was linked")
    want=[]
    for rel, _pairs, _mode in FRAGRANCE_GIFT_LINKS:
        folder=rel[:-len("index.html")] if rel.endswith("index.html") else rel
        if not folder.endswith("/"): folder+="/"
        want.append(f"{PREFIX}/{folder}" if not folder.startswith("/") else f"{PREFIX}{folder}")
    if sorted(want)!=frag:
        raise SystemExit(f"fragrance gift guides: sitemap fragrance urls drifted ({len(frag)} sitemap, {len(want)} linked)")
    counts=[]
    for rel, pairs, mode in FRAGRANCE_GIFT_LINKS:
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if FRAGRANCE_GIFT_MARK in text:
            raise SystemExit(f"{rel}: gift guide marker was not replaced")
        anchors=_section_chip_anchors(rel, FRAGRANCE_GIFT_HEADING)
        specific=[(href, label) for href, label in anchors if _href_path(href).startswith(f"{PREFIX}/gifts/") and _href_path(href)!=f"{PREFIX}/gifts/"]
        if [ (f"{PREFIX}/gifts/{gslug}/", title) for gslug, title in pairs ]!=specific:
            raise SystemExit(f"{rel}: sitemap audit gift links drifted")
        if len(specific)<1:
            raise SystemExit(f"{rel}: no specific gift guide link")
        if mode=="fallback" and not (2<=len(specific)<=3):
            raise SystemExit(f"{rel}: fallback should be 2 or 3 guides")
        for href, label in specific:
            path=_href_path(href)
            if path not in paths:
                raise SystemExit(f"{rel}: {href} is not in the sitemap")
            local=path[len(PREFIX):] if PREFIX and path.startswith(PREFIX) else path
            if not os.path.isfile(f"{OUT}{local}index.html"):
                raise SystemExit(f"{rel}: {href} has no built page")
        counts.append(len(specific))
    print(f"fragrance gift guides: {len(frag)} sitemap pages, min {min(counts)} max {max(counts)} specific guide links")
VS_GIFT_HEADING="Gift guides featuring these fragrances"
VS_GIFT_LINKS=[]
def guides_featuring_either(ds):
    """Gift pages whose rendered list includes any of these bottles, in the order the pages were built."""
    hits=set()
    for d in ds:
        hits.update(guides_featuring_deal(d))
    return [gslug for gslug, _title, picks in GIFT_PAGE_PICKS if gslug in hits]
def guides_featuring_brands(names):
    """Gift pages that include a checked deal from these brands. Same inclusion rule as brand pages."""
    wanted={canon(b) for b in names if b}
    rows=[d for d in deals if canon(d.get("brand") or "") in wanted]
    seen=set(); out=[]
    for gslug, _title in _guides_featuring(rows):
        if gslug in seen: continue
        seen.add(gslug)
        out.append(gslug)
    return out
def apply_vs_gift_guides():
    """Splice 'Gift guides featuring these fragrances' onto each /vs/ page.

    A guide is linked when its rendered list includes either compared bottle.
    When neither bottle is on a guide, link guides that include another checked
    deal from the same brand. When neither brand is on a guide, link the /gifts/ hub.
    """
    global VS_GIFT_LINKS
    if not VS_PAGES:
        raise SystemExit("vs gift guides: no comparison pages")
    if len(VS_PAGES)!=len(VS):
        raise SystemExit(f"vs gift guides: {len(VS_PAGES)} pages for {len(VS)} comparisons")
    if len(VS_PAGES)!=len({rel for rel,_ in VS_PAGES}):
        raise SystemExit("vs gift guides: two comparisons wrote the same page")
    by_slug=dict(GIFT_SUBPAGES)
    for gslug, title, _picks in GIFT_PAGE_PICKS:
        if by_slug.get(gslug)!=title:
            raise SystemExit(f"vs gift guides: {gslug} title {title!r} != registered {by_slug.get(gslug)!r}")
    picks_by={gslug: picks for gslug, _title, picks in GIFT_PAGE_PICKS}
    hub_href=f"{PREFIX}/gifts/"
    hub_title=_page_h1("gifts/index.html")
    VS_GIFT_LINKS=[]
    counts=[]
    for rel, v in VS_PAGES:
        A,B=v["A"],v["B"]
        featured=guides_featuring_either([A,B])
        extra=()
        if featured:
            pairs=[(gslug, by_slug[gslug]) for gslug in featured]
            mode="featured"
        else:
            branded=guides_featuring_brands([A.get("brand"), B.get("brand")])
            if branded:
                pairs=[(gslug, by_slug[gslug]) for gslug in branded]
                mode="brand"
            else:
                pairs=[]
                mode="hub"
                extra=((hub_href, hub_title),)
        if mode!="hub" and not pairs:
            raise SystemExit(f"{rel}: no gift guide for {v.get('slug')}")
        if mode=="featured" and guides_featuring_either([A,B])!=[s for s,_ in pairs]:
            raise SystemExit(f"{rel}: featured guides drifted")
        if mode=="brand" and guides_featuring_either([A,B]):
            raise SystemExit(f"{rel}: brand fallback used although a compared fragrance is listed")
        if mode=="featured":
            for gslug, _title in pairs:
                if not any(_pick_features_deal(p, d) for d in (A,B) for p in (picks_by.get(gslug) or [])):
                    raise SystemExit(f"{rel}: {gslug} does not include either fragrance")
        if mode=="brand":
            wanted={canon(A.get("brand")), canon(B.get("brand"))}
            keys={_deal_key(d) for d in deals if canon(d.get("brand") or "") in wanted}
            for gslug, _title in pairs:
                if not any(_deal_key(p) in keys for p in (picks_by.get(gslug) or [])):
                    raise SystemExit(f"{rel}: {gslug} does not include either brand")
        _splice_mark(rel, VS_GIFT_MARK, gift_guide_section(VS_GIFT_HEADING, pairs, extra))
        got=_section_anchors(rel, VS_GIFT_HEADING)
        expect=[(f"{PREFIX}/gifts/{gslug}/", title) for gslug, title in pairs]+[(href, label) for href, label in extra]
        if got!=expect:
            raise SystemExit(f"{rel}: gift guide section drifted")
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if VS_GIFT_MARK in text:
            raise SystemExit(f"{rel}: gift guide marker was not replaced")
        if text.count(VS_GIFT_HEADING)!=1:
            raise SystemExit(f"{rel}: expected one {VS_GIFT_HEADING} section")
        if not got:
            raise SystemExit(f"{rel}: gift guide section is empty")
        for href, label in got:
            path=_href_path(href)
            if path==hub_href:
                if mode!="hub" or label!=hub_title:
                    raise SystemExit(f"{rel}: unexpected /gifts/ hub link")
                continue
            gslug=path[len(f"{PREFIX}/gifts/"):].strip("/")
            if "/" in gslug or gslug not in by_slug or label!=by_slug[gslug]:
                raise SystemExit(f"{rel}: anchor {label!r} is not a built guide title")
            if not os.path.isfile(f"{OUT}/gifts/{gslug}/index.html"):
                raise SystemExit(f"{rel}: {path} was not built")
            if not picks_by.get(gslug):
                raise SystemExit(f"{rel}: {gslug} has no deals")
        specific=len(pairs)
        if mode=="hub" and specific:
            raise SystemExit(f"{rel}: hub fallback still linked a guide")
        if mode!="hub" and specific<1:
            raise SystemExit(f"{rel}: no specific gift guide link")
        counts.append(specific)
        VS_GIFT_LINKS.append((rel, list(pairs), mode, list(extra)))
        shown=", ".join(s for s,_ in pairs) if pairs else hub_href
        print(f"vs gift guides: {v['slug']} -> {specific} ({mode}): {shown}")
    print(f"vs gift guides: {len(counts)} pages, min {min(counts)} max {max(counts)} specific guide links")
def _sitemap_paths():
    text=open(f"{OUT}/sitemap.xml", encoding="utf-8").read()
    out=set()
    for loc in re.findall(r"<loc>([^<]+)</loc>", text):
        path=urllib.parse.urlparse(html.unescape(loc)).path or "/"
        if not path.endswith("/"): path+="/"
        out.add(path)
    return out
def _href_path(href):
    path=html.unescape(href).split("?")[0].split("#")[0]
    if not path.startswith("/"):
        raise SystemExit(f"dupe link is not root-relative: {href}")
    if not path.endswith("/"): path+="/"
    return path
def audit_dupe_related():
    """Related-dupe and gift-guide chips on every /dupe/ page resolve to sitemap URLs."""
    paths=_sitemap_paths()
    by_slug=dict(GIFT_SUBPAGES)
    if not DUPE_PAGES:
        raise SystemExit("dupe related audit: no dupe pages")
    for rel, d in DUPE_PAGES:
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if DUPE_GIFT_MARK in text:
            raise SystemExit(f"{rel}: gift guide marker was not replaced")
        if "<h2>More dupes</h2>" in text:
            raise SystemExit(f"{rel}: old More dupes block is still on the page")
        related=_section_anchors(rel, "Related dupes")
        gifts=_section_anchors(rel, "Gift guides")
        if text.count(">Related dupes</h2>")!=1 or text.count(">Gift guides</h2>")!=1:
            raise SystemExit(f"{rel}: expected one Related dupes and one Gift guides section")
        for href, _label in related+gifts:
            path=_href_path(href)
            if path not in paths:
                raise SystemExit(f"{rel}: {href} is not in the sitemap")
            local=path[len(PREFIX):] if PREFIX and path.startswith(PREFIX) else path
            if not os.path.isfile(f"{OUT}{local.rstrip('/')}/index.html") and local.rstrip("/") not in ("",):
                # /dupes/ is dupes/index.html; a trailing-slash path maps to that directory.
                if not os.path.isfile(f"{OUT}{local}index.html"):
                    raise SystemExit(f"{rel}: {href} has no built page")
        hb=hub_of(d)
        dupe_links=[href for href, _label in related if _href_path(href).startswith(f"{PREFIX}/dupe/")]
        if hb:
            if not related or _href_path(related[0][0])!=f"{PREFIX}/dupes/{hb['slug']}/":
                raise SystemExit(f"{rel}: related dupes should lead with /dupes/{hb['slug']}/")
        elif any(_href_path(href).startswith(f"{PREFIX}/dupes/") and _href_path(href)!=f"{PREFIX}/dupes/" for href, _label in related):
            raise SystemExit(f"{rel}: linked a dupe hub this original does not belong to")
        if not 1<=len(dupe_links)<=6:
            raise SystemExit(f"{rel}: expected 1–6 sibling dupe links, got {len(dupe_links)}")
        if _href_path(related[-1][0])!=f"{PREFIX}/dupes/":
            raise SystemExit(f"{rel}: related dupes should keep the /dupes/ index link")
        self_path=_href_path(dupe_href(d))
        if self_path in {_href_path(href) for href, _label in related}:
            raise SystemExit(f"{rel}: related dupes links to itself")
        expect_sibs=[_href_path(dupe_href(x)) for x in related_dupe_picks(d, 6)]
        if [_href_path(href) for href in dupe_links]!=expect_sibs:
            raise SystemExit(f"{rel}: sibling order drifted from same-original / same-house ranking")
        for sib in D["dupes"]:
            if sib is d or sib.get("original")!=d.get("original"): continue
            if _href_path(dupe_href(sib)) not in expect_sibs:
                raise SystemExit(f"{rel}: missing the other {sib['original']} dupe")
        if not 2<=len(gifts)<=4:
            raise SystemExit(f"{rel}: expected 2–4 gift guides, got {len(gifts)}")
        expect=[(f"{PREFIX}/gifts/{slug}/", title) for slug, title in gift_links_for_dupe(d, by_slug)]
        if gifts!=expect:
            raise SystemExit(f"{rel}: gift guides drifted")
        for href, label in gifts:
            path=_href_path(href)
            if path==f"{PREFIX}/gifts/":
                raise SystemExit(f"{rel}: gift block links the hub instead of a guide")
            slug=path[len(f"{PREFIX}/gifts/"):].strip("/")
            if slug not in by_slug or label!=by_slug[slug]:
                raise SystemExit(f"{rel}: gift anchor {label!r} is not a built guide title")
    print(f"dupe related links: {len(DUPE_PAGES)} pages, sibling and gift-guide hrefs are in the sitemap")
def audit_dupe_deal_cards():
    """Every dupe page renders at least 6 cards whose prices are deals.json rows."""
    card_re=re.compile(r'<article class="card">(.*?)</article>', re.S)
    price_re=re.compile(r'<span class="price">\$([0-9]+\.[0-9]{2})</span>')
    was_re=re.compile(r'<span class="was">\$([0-9]+\.[0-9]{2})</span>')
    if len(DUPE_PAGES)!=len(D["dupes"]):
        raise SystemExit(f"dupe deal cards: {len(DUPE_PAGES)} pages for {len(D['dupes'])} dupes")
    checked={(d["id"], f"{d['price']:.2f}", f"{d['was']:.2f}") for d in deals if _card_deal_ok(d)}
    for rel, d in DUPE_PAGES:
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        picked=DUPE_DEAL_PICKS.get(id(d))
        if not picked:
            raise SystemExit(f"{rel}: no deal-card pick recorded")
        expect=picked["exact"]+picked["similar"]
        cards=card_re.findall(text)
        if len(cards)<DUPE_DEAL_TARGET or len(cards)!=len(expect):
            raise SystemExit(f"{rel}: {len(cards)} deal cards, expected {len(expect)}")
        if picked["exact"]:
            if text.count(">Matching deals in stock now</h2>")!=1:
                raise SystemExit(f"{rel}: missing the matching-deals heading")
        else:
            if text.count(">Similar deals in stock now</h2>")!=1:
                raise SystemExit(f"{rel}: missing the similar-deals heading")
            if "not in today" not in text:
                raise SystemExit(f"{rel}: fallback copy does not say the exact fragrance is absent")
        for body, deal in zip(cards, expect):
            key=(deal["id"], f"{deal['price']:.2f}", f"{deal['was']:.2f}")
            if key not in checked:
                raise SystemExit(f"{rel}: card {deal.get('id')} is not a checked deal")
            pm, wm=price_re.search(body), was_re.search(body)
            if not pm or pm.group(1)!=key[1] or not wm or wm.group(1)!=key[2]:
                raise SystemExit(f"{rel}: card price drifted from deals.json for {deal.get('id')}")
            frag=f"/fragrance/{slug(deal['brand']+' '+deal['name'])}/"
            if frag not in body or f"Buy at {e(deal['retailer'])}" not in body:
                raise SystemExit(f"{rel}: card for {deal.get('id')} is missing its deal link or button")
        if text.count(">Related dupes</h2>")!=1 or text.count(">Gift guides</h2>")!=1:
            raise SystemExit(f"{rel}: deal cards disturbed related dupes or gift guides")
    print(f"dupe deal cards: {len(DUPE_PAGES)} pages, each with at least {DUPE_DEAL_TARGET} priced cards from deals.json")
def apply_gift_guide_links():
    """Write hub, homepage, and sibling links from the guides this build just created."""
    root=f"{BASE}{PREFIX}/gifts/"
    sitemap_slugs=[]
    for u in PAGES:
        if u==root or not u.startswith(root): continue
        slug=u[len(root):].strip("/")
        if slug: sitemap_slugs.append(slug)
    registered=[slug for slug,_ in GIFT_SUBPAGES]
    if registered!=sitemap_slugs:
        raise SystemExit("gift guide links drifted from the sitemap: registered "+repr(registered)+" sitemap "+repr(sitemap_slugs))
    for slug, title in GIFT_SUBPAGES:
        h1=_page_h1(f"gifts/{slug}/index.html")
        if h1!=title:
            raise SystemExit(f"gift guide {slug}: link title {title!r} is not the page h1 {h1!r}")
    by_slug=dict(GIFT_SUBPAGES)
    home_pairs=[(slug, by_slug[slug]) for slug in HOME_GIFT_SLUGS if slug in by_slug]
    if len(home_pairs)<4:
        raise SystemExit("homepage holiday gift guides: fewer than 4 guides were generated")
    hub_html=gift_guide_section("Gift guides", GIFT_SUBPAGES)
    home_html=gift_guide_section("Holiday gift guides", home_pairs, extra=((f"{PREFIX}/gifts/", "All holiday gift guides"),))
    _splice_mark("gifts/index.html", GIFT_HUB_MARK, hub_html)
    _splice_mark("index.html", GIFT_HOME_MARK, home_html)
    for slug, title in GIFT_SUBPAGES:
        others=[(s, t) for s, t in GIFT_SUBPAGES if s!=slug]
        _splice_mark(f"gifts/{slug}/index.html", GIFT_MORE_MARK, gift_guide_section("More gift guides", others))
    apply_brand_gift_guides()
    apply_dupe_gift_guides()
    apply_fragrance_gift_guides()
    apply_vs_gift_guides()
    for dirpath, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"): continue
            path=os.path.join(dirpath, fn)
            text=open(path, encoding="utf-8").read()
            for mark in (GIFT_HUB_MARK, GIFT_HOME_MARK, GIFT_MORE_MARK, BRAND_GIFT_MARK, DUPE_GIFT_MARK, FRAGRANCE_GIFT_MARK, VS_GIFT_MARK):
                if mark in text:
                    raise SystemExit(f"{os.path.relpath(path, OUT)}: still contains {mark}")
    hub_links=_section_anchors("gifts/index.html", "Gift guides")
    expect=[(f"{PREFIX}/gifts/{slug}/", title) for slug, title in GIFT_SUBPAGES]
    if hub_links!=expect:
        raise SystemExit("hub Gift guides section does not list every gift page by its title")
    home_links=_section_anchors("index.html", "Holiday gift guides")
    home_expect=[(f"{PREFIX}/gifts/{slug}/", title) for slug, title in home_pairs]+[(f"{PREFIX}/gifts/", "All holiday gift guides")]
    if home_links!=home_expect:
        raise SystemExit("homepage Holiday gift guides section is missing a guide or the /gifts/ link")
    for slug, title in GIFT_SUBPAGES:
        more=_section_anchors(f"gifts/{slug}/index.html", "More gift guides")
        more_expect=[(f"{PREFIX}/gifts/{s}/", t) for s, t in GIFT_SUBPAGES if s!=slug]
        if more!=more_expect:
            raise SystemExit(f"{slug}: More gift guides does not link the other gift pages")
    print(f"gift guide links: {len(GIFT_SUBPAGES)} subpages listed on /gifts/ by page title; homepage links {len(home_pairs)} plus /gifts/")
apply_gift_guide_links()
# ---------- Black Friday & Cyber Monday (/black-friday-fragrance-deals/) ----------
# Generated from deals.json on every build, including the daily refresh, so the
# rows and the last-updated line move with the price check. No prices are invented.
def bf_require(rows):
    """A card on this page must already have a retailer image and a checked price."""
    bad=[]
    for d in rows:
        if not retailer_image(d) or isinstance(d.get("price"), bool) or not isinstance(d.get("price"), (int, float)):
            bad.append(d.get("id") or fullname(d))
    if bad:
        raise SystemExit("black friday page: card lacks an image or price: "+", ".join(bad[:20]))
    return rows
bf_singles=[d for d in deals if gift_ok(d) and not is_gift_set(d)]
bf_men=bf_require(sorted([d for d in bf_singles if d["gender"]=="men"], key=lambda d:(-(d.get("pct_off") or 0), d["price"], d["id"])))
bf_women=bf_require(sorted([d for d in bf_singles if d["gender"]=="women"], key=lambda d:(-(d.get("pct_off") or 0), d["price"], d["id"])))
bf_sets=bf_require(by_price(list(boxed)))
bf_u50=bf_require(sorted([d for d in bf_singles if d["price"]<50], key=lambda d:(d["price"], -(d.get("pct_off") or 0), d["id"])))
bf_sections=[
 ("mens","Men's cologne","Men's colognes from the deals we checked, largest discount first. Unisex bottles are not listed in this section.",
  bf_men,"Men's Black Friday cologne deals"),
 ("womens","Women's perfume","Women's perfumes from the deals we checked, largest discount first.",
  bf_women,"Women's Black Friday perfume deals"),
 ("gift-sets","Gift sets","Boxed sets we checked. A single bottle is not listed in this section. Lowest price first.",
  bf_sets,"Black Friday fragrance gift sets"),
 ("under-50","Under $50","Single bottles under $50, lowest price first, including unisex. A bottle already shown under men's or women's can appear here again. Boxed sets stay in the gift sets section.",
  bf_u50,"Fragrance deals under $50"),
]
bf_parts=[]
bf_ld=[]
for anchor,heading,blurb,rows,list_name in bf_sections:
    block=f"<h2 id='{anchor}'>{e(heading)}</h2><p>{e(blurb)}</p>"
    if rows:
        block+=gift_table(rows)
        bf_ld.append(itemlist(rows, list_name))
    else:
        block+="<div class='box'><p>None of the deals we checked today fit this section.</p></div>"
    bf_parts.append(block)
bf_ids=[]
for _,_,_,rows,_ in bf_sections:
    for d in rows:
        if d["id"] not in bf_ids: bf_ids.append(d["id"])
bf_cards=sum(len(rows) for _,_,_,rows,_ in bf_sections)
bf_when=f"{upd:%b %-d, %Y}"
bf_noun="checked pick" if len(bf_ids)==1 else "checked picks"
bf_h1="Black Friday perfume deals 2026"
bf_title=f"Black Friday Perfume Deals 2026 | {NAME}"
bf_desc=f"Black Friday perfume deals 2026 and Cyber Monday cologne deals: {len(bf_ids)} {bf_noun} for men's, women's, gift sets, and under $50. Last updated {bf_when}."
if len(bf_title)>60 or "black friday perfume deals 2026" not in bf_title.lower():
    raise SystemExit(f"black friday title is {len(bf_title)} chars or misses the target phrase")
if not (70<=len(bf_desc)<=160) or "cyber monday cologne deals" not in bf_desc.lower() or "black friday perfume deals 2026" not in bf_desc.lower():
    raise SystemExit(f"black friday meta is {len(bf_desc)} chars or misses a target phrase")
bf_intro=("Black Friday 2026 is November 27 and Cyber Monday 2026 is November 30. "
 "Cyber Monday cologne deals sit with the men's cologne and the under-$50 rows. "
 "Every card is a deal already in the price check, using that product's stored photo and price. "
 "This page rebuilds with the daily refresh.")
bf_faqs=[
 ("When is Black Friday 2026?",
  "Black Friday 2026 is Friday, November 27, 2026, the day after Thanksgiving."),
 ("When is Cyber Monday 2026?",
  "Cyber Monday 2026 is Monday, November 30, 2026."),
 ("Are these prices a separate Black Friday or Cyber Monday sale?",
  f"No. Each price is one we already checked at an authorized retailer, and each photo is the one stored for that product. Last updated {bf_when}. The page is rebuilt with the daily refresh, so a product drops off when it is no longer a checked deal."),
 ("Do gift sets and bottles under $50 have their own sections?",
  "Yes. Men's cologne, women's perfume, boxed gift sets, and single bottles under $50 are separate sections. A set is listed only when the deal data already calls it a set."),
]
bf_jumps="<p class='chips'>"+"".join(f"<a href='#{anchor}'>{e(heading)}</a>" for anchor,heading,_,_,_ in bf_sections)+"</p>"
use_sid("bfcm", "fragrance-deals")
page("black-friday-fragrance-deals/index.html", bf_title, bf_desc,
 f"<h1>{e(bf_h1)}</h1><p class='sub'>Last updated {e(bf_when)}. Checked {upd_h}.</p><p>{e(bf_intro)}</p>{gift_nav()}{bf_jumps}{GIFT_DISC}{''.join(bf_parts)}{faqhtml(bf_faqs)}{BREVO_FORM}<p class='meta'>Prices and photos come from the deals we already checked. We do not invent a price or a photo, and we do not list testers, decants, or Amazon.</p>",
 bf_ld+[faqld(bf_faqs)], image="/media/pins/holiday-fragrance-gifts.png", feed=bool(bf_ids))
KW+=["black friday perfume deals 2026","cyber monday cologne deals"]
print(f"black friday page: {len(bf_ids)} unique deals, {bf_cards} cards; men {len(bf_men)}, women {len(bf_women)}, sets {len(bf_sets)}, under $50 {len(bf_u50)}")
# ---------- 404 (GitHub Pages serves site/404.html for any unknown path) ----------
def write_404():
    """Branded not-found page using the same header, footer, and CSS as every other page.

    index=False keeps it out of PAGES, so the sitemap rewrite, llms.txt, the RSS feed,
    and IndexNow (which submits sitemap.xml) never see it.
    Links are root-relative because this file is served at whatever path was requested.
    Gift-guide links are GIFT_SUBPAGES, the same list the /gifts/ hub just wrote.
    Deal cards are the checked deals only. No price is typed in by hand.
    """
    use_sid("404")
    if not GIFT_SUBPAGES:
        raise SystemExit("404 page: gift guide list is empty")
    entry=[(f"{PREFIX}/","Homepage"),(f"{PREFIX}/gifts/","Holiday gifts"),
           (f"{PREFIX}/men/","Men's deals"),(f"{PREFIX}/women/","Women's deals")]
    start=("<section class='box'><h2 style='margin-top:0'>Start here</h2><div class='chips'>"
           +"".join(f"<a href='{href}'>{e(label)}</a>" for href,label in entry)+"</div></section>")
    guides=gift_guide_section("Gift guides", GIFT_SUBPAGES)
    top=[d for d in deals if isinstance(d.get("price"),(int,float)) and not isinstance(d.get("price"),bool)
         and isinstance(d.get("was"),(int,float)) and not isinstance(d.get("was"),bool)
         and d.get("url") and d.get("retailer")][:4]
    deals_html=""
    if top:
        deals_html=("<h2>A few of today's top deals</h2>"
                    "<p class='sub'>Largest checked discount first. Prices are the ones we checked.</p>"
                    f"<div class='grid'>{''.join(card(d) for d in top)}</div>")
    page("404.html", f"Page not found | {NAME}",
         "That page isn't on ScentDealsDaily. Browse today's fragrance deals, the holiday gift guides, and men's and women's deals.",
         "<h1>Page not found</h1><p class='sub'>That page isn't on ScentDealsDaily. The link may be old, or the address was mistyped.</p>"
         +start+guides+deals_html,
         index=False)
    text=open(f"{OUT}/404.html",encoding="utf-8").read()
    if '<meta name="robots" content="noindex">' not in text:
        raise SystemExit("404.html missing noindex")
    if "<h1>Page not found</h1>" not in text:
        raise SystemExit("404.html missing not-found heading")
    if any(u.rstrip("/").endswith("/404.html") for u in PAGES):
        raise SystemExit("404 page was added to the page index")
    refs=[html.unescape(a or b).strip() for a,b in re.findall(r"""(?:href|src|srcset)\s*=\s*(?:"([^"]*)"|'([^']*)')""", text)]
    for ref in refs:
        if not ref or ref.startswith(("#","mailto:","tel:","javascript:","data:","http://","https://","/")):
            continue
        raise SystemExit(f"404.html link is not root-relative or absolute: {ref}")
    if _section_anchors("404.html","Gift guides")!=_section_anchors("gifts/index.html","Gift guides"):
        raise SystemExit("404 gift guides drifted from the /gifts/ hub")
    for href,label in entry:
        if f"<a href='{href}'>{e(label)}</a>" not in text:
            raise SystemExit(f"404.html missing entry link {label} {href}")
    intro=re.search(r"<h1>Page not found</h1><p class='sub'>(.*?)</p>", text)
    if not intro or "$" in intro.group(1):
        raise SystemExit("404 intro is missing or states a price")
    for d in top:
        price=f"${d['price']:.2f}"
        was=f"${d['was']:.2f}"
        if price not in text or was not in text:
            raise SystemExit(f"404 card missing the checked price for {d.get('id')}")
    print(f"404.html: {len(GIFT_SUBPAGES)} gift guides, {len(top)} top deals, noindex")
write_404()
def assert_404_unlisted():
    """sitemap.xml and llms.txt are what crawlers and IndexNow read. The feed is the same set."""
    for rel in ("sitemap.xml","llms.txt","feed.xml"):
        blob=open(f"{OUT}/{rel}",encoding="utf-8").read()
        if "404.html" in blob:
            raise SystemExit(f"{rel} lists the 404 page")
    n=len(re.findall(r"<loc>", open(f"{OUT}/sitemap.xml",encoding="utf-8").read()))
    if n!=len(PAGES):
        raise SystemExit(f"sitemap has {n} urls, page index has {len(PAGES)}")
    print(f"404.html excluded from sitemap ({n} urls), llms.txt, feed.xml, and IndexNow")
# rewrite sitemap with new pages + keyword list + IndexNow key
open(f"{OUT}/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join(f"<url><loc>{u}</loc><lastmod>{upd:%Y-%m-%d}</lastmod></url>" for u in PAGES)+"</urlset>\n")
def audit_vs_gift_links():
    """Every sitemap /vs/ URL links the gift guides that list either bottle, or the /gifts/ hub."""
    paths=_sitemap_paths()
    vs_urls=sorted(p for p in paths if p.startswith(f"{PREFIX}/vs/"))
    if not VS_GIFT_LINKS:
        raise SystemExit("vs gift guides: nothing was linked")
    want=[]
    for rel, _pairs, _mode, _extra in VS_GIFT_LINKS:
        folder=rel[:-len("index.html")] if rel.endswith("index.html") else rel
        if not folder.endswith("/"): folder+="/"
        want.append(f"{PREFIX}/{folder}" if not folder.startswith("/") else f"{PREFIX}{folder}")
    if sorted(want)!=vs_urls:
        raise SystemExit(f"vs gift guides: sitemap comparison urls drifted ({len(vs_urls)} sitemap, {len(want)} linked)")
    hub=f"{PREFIX}/gifts/"
    by_slug=dict(GIFT_SUBPAGES)
    counts=[]
    for rel, pairs, mode, extra in VS_GIFT_LINKS:
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        if VS_GIFT_MARK in text:
            raise SystemExit(f"{rel}: gift guide marker was not replaced")
        anchors=_section_anchors(rel, VS_GIFT_HEADING)
        specific=[(href, label) for href, label in anchors if _href_path(href).startswith(f"{PREFIX}/gifts/") and _href_path(href)!=hub]
        expect=[(f"{PREFIX}/gifts/{gslug}/", title) for gslug, title in pairs]
        if specific!=expect:
            raise SystemExit(f"{rel}: sitemap audit gift links drifted")
        if mode=="hub":
            if specific or anchors!=[(hub, _page_h1("gifts/index.html"))]:
                raise SystemExit(f"{rel}: hub fallback should be the only gift link")
        elif len(specific)<1:
            raise SystemExit(f"{rel}: no specific gift guide link")
        for href, label in anchors:
            path=_href_path(href)
            if path not in paths:
                raise SystemExit(f"{rel}: {href} is not in the sitemap")
            local=path[len(PREFIX):] if PREFIX and path.startswith(PREFIX) else path
            if not os.path.isfile(f"{OUT}{local}index.html"):
                raise SystemExit(f"{rel}: {href} has no built page")
            if path==hub: continue
            gslug=path[len(f"{PREFIX}/gifts/"):].strip("/")
            if gslug not in by_slug or label!=by_slug[gslug]:
                raise SystemExit(f"{rel}: {label!r} is not a gift guide title")
        if mode!="hub" and extra:
            raise SystemExit(f"{rel}: a specific guide list also links the hub")
        counts.append(len(specific))
    print(f"vs gift guides: {len(vs_urls)} sitemap pages, min {min(counts)} max {max(counts)} specific guide links")
audit_dupe_related()
audit_dupe_deal_cards()
audit_fragrance_gift_links()
audit_vs_gift_links()
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
with open(f"{OUT}/llms.txt","a") as f: f.write("\n## Buying guides & dupe comparisons\n"+"\n".join(u for u in PAGES if "/best/" in u or "/vs/" in u or "/gifts/" in u or "/black-friday-fragrance-deals/" in u or any(f"/dupes/{h['slug']}/" in u for h in HUBS))+"\n")
assert_404_unlisted()
print(len(PAGES),"pages total;",len(KW),"keywords;",nfeed,"feed items")
if _media_tmp:
    shutil.copytree(f"{_media_tmp}/media", f"{OUT}/media")
    shutil.rmtree(_media_tmp)
    print("copied site/media ->", OUT)
if _MEDIA_BEFORE:
    # Gift pins are rewritten every build. Everything else in site/media stays byte-for-byte.
    changed=[rel for rel,digest in _MEDIA_BEFORE.items() if rel not in _GIFT_PINS_WRITTEN and (not os.path.isfile(f"{OUT}/media/{rel}") or _sha256_file(f"{OUT}/media/{rel}")!=digest)]
    if changed:
        raise SystemExit("existing media changed or deleted: "+", ".join(changed[:12]))
    print(f"media preserved: {len(_MEDIA_BEFORE)-len(_GIFT_PINS_WRITTEN & set(_MEDIA_BEFORE))} existing files unchanged")

# Parent crumb labels. The current page uses its own h1. A section missing from
# the built files is not linked, so /fragrance/, /dupe/, /best/, and /vs/ stay
# two-level trails (Home > this page) instead of pointing at a missing index.
SECTION_LABELS={
    "gifts":"Gift guides",
    "brands":"Brands",
    "dupes":"Dupes",
    "men":"Men's cologne",
    "women":"Women's perfume",
    "unisex":"Unisex fragrance",
}
def _html_rels():
    found=[]
    for dirpath,_,files in os.walk(OUT):
        for fn in files:
            if fn.endswith(".html"):
                found.append(os.path.relpath(os.path.join(dirpath,fn), OUT).replace(os.sep,"/"))
    return found
def _canon_of(text, rel):
    m=re.search(r'<link rel="canonical" href="([^"]*)"', text)
    if not m: raise SystemExit(f"{rel}: missing canonical")
    return html.unescape(m.group(1))
def _h1_of(text, rel):
    m=re.search(r"<h1>(.*?)</h1>", text, re.S)
    if not m: raise SystemExit(f"{rel}: no h1 for breadcrumb")
    name=html.unescape(re.sub(r"<[^>]+>","", m.group(1))).strip()
    if not name: raise SystemExit(f"{rel}: empty h1 for breadcrumb")
    return name
def _url_path(canonical):
    path=urllib.parse.urlparse(canonical).path or "/"
    return path if path.startswith("/") else "/"+path
def _prefix_parts():
    return [p for p in (PREFIX or "").strip("/").split("/") if p]
def _ancestor_paths(path):
    parts=[p for p in path.strip("/").split("/") if p]
    return ["/"+"/".join(parts[:i])+"/" for i in range(1,len(parts))]
def _section_key(path):
    """First path segment below PATH_PREFIX when this URL is a section index, else None."""
    parts=[p for p in path.strip("/").split("/") if p]
    pre=_prefix_parts()
    if pre and parts[:len(pre)]==pre: parts=parts[len(pre):]
    return parts[0] if len(parts)==1 else None
def _crumb_name(path, h1):
    key=_section_key(path)
    if key and key in SECTION_LABELS: return SECTION_LABELS[key]
    return h1
def _ld_scripts(text):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
def _load_pages():
    pages={}
    by_path={}
    for rel in _html_rels():
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        canon=_canon_of(text, rel)
        path=_url_path(canon)
        if path in by_path:
            raise SystemExit(f"duplicate canonical path {path}: {by_path[path]} and {rel}")
        info={"rel":rel,"text":text,"canon":canon,"path":path,"h1":_h1_of(text, rel)}
        pages[rel]=info
        by_path[path]=rel
    if by_path.get("/")!="index.html":
        raise SystemExit(f"homepage canonical path did not resolve to index.html ({by_path.get('/')})")
    return pages, by_path
def _crumbs_for(info, pages, by_path):
    """Home, then each ancestor that was actually built, then this page."""
    home=pages["index.html"]
    crumbs=[("Home", home["canon"], home["path"])]
    for ap in _ancestor_paths(info["path"]):
        if ap==home["path"]: continue
        parent=by_path.get(ap)
        if not parent: continue
        pinfo=pages[parent]
        crumbs.append((_crumb_name(ap, pinfo["h1"]), pinfo["canon"], pinfo["path"]))
    crumbs.append((info["h1"], info["canon"], None))
    return crumbs
def _crumb_nav(crumbs):
    bits=[]
    for i,(name,_url,href) in enumerate(crumbs):
        if i: bits.append('<span class="sep" aria-hidden="true">&gt;</span>')
        if href: bits.append(f'<a href="{e(href)}">{e(name)}</a>')
        else: bits.append(f'<span aria-current="page">{e(name)}</span>')
    return '<nav class="crumbs" aria-label="Breadcrumb">'+"".join(bits)+"</nav>"
def _crumb_ld(crumbs):
    ld={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":name,"item":url} for i,(name,url,_href) in enumerate(crumbs)]}
    payload=json.dumps(ld, ensure_ascii=False).replace("<","\\u003c")
    return f'<script type="application/ld+json">{payload}</script>'
def apply_breadcrumbs():
    """Insert the trail and its JSON-LD after every page exists, so a hub counts only if it was built."""
    pages, by_path=_load_pages()
    n=0
    hub_n=0
    for rel,info in pages.items():
        if rel in ("index.html","404.html"): continue
        before=_ld_scripts(info["text"])
        crumbs=_crumbs_for(info, pages, by_path)
        if len(crumbs)<2: raise SystemExit(f"{rel}: breadcrumb is missing the current page")
        if len(crumbs)>2: hub_n+=1
        nav=_crumb_nav(crumbs)
        script=_crumb_ld(crumbs)
        text=info["text"]
        if text.count("<main>")!=1: raise SystemExit(f"{rel}: expected one <main> for the breadcrumb")
        if text.count("</head>")!=1: raise SystemExit(f"{rel}: expected one </head>")
        text=text.replace("<main>","<main>"+nav,1).replace("</head>",script+"</head>",1)
        open(f"{OUT}/{rel}","w",encoding="utf-8").write(text)
        after=_ld_scripts(text)
        if after[:-1]!=before:
            raise SystemExit(f"{rel}: existing JSON-LD was changed while adding the breadcrumb")
        n+=1
    print(f"breadcrumbs: {n} pages ({hub_n} with a section hub); skipped homepage and 404")
def _walk_type(node, typ, acc):
    if isinstance(node, dict):
        t=node.get("@type")
        if t==typ or (isinstance(t, list) and typ in t): acc.append(node)
        for v in node.values(): _walk_type(v, typ, acc)
    elif isinstance(node, list):
        for v in node: _walk_type(v, typ, acc)
def audit_breadcrumbs():
    """Every sitemap URL except the homepage has one BreadcrumbList whose last item is that canonical.
    Every crumb URL is a page this build wrote. Homepage and 404 have neither trail nor schema."""
    pages, by_path=_load_pages()
    by_canon={info["canon"]:rel for rel,info in pages.items()}
    bad=[]
    sitemap=open(f"{OUT}/sitemap.xml", encoding="utf-8").read()
    locs=re.findall(r"<loc>([^<]+)</loc>", sitemap)
    home=pages["index.html"]["canon"]
    if home not in locs: bad.append("homepage missing from sitemap")
    seen=set()
    with_hub=0
    skipped_section=0
    for rel,info in pages.items():
        text=open(f"{OUT}/{rel}", encoding="utf-8").read()
        blocks=[]
        for raw in _ld_scripts(text):
            try: blocks.append(json.loads(raw))
            except json.JSONDecodeError as ex:
                bad.append(f"{rel}: JSON-LD did not parse ({ex})")
        found=[]
        for block in blocks: _walk_type(block, "BreadcrumbList", found)
        navs=re.findall(r'<nav class="crumbs" aria-label="Breadcrumb">(.*?)</nav>', text, re.S)
        if rel in ("index.html","404.html"):
            if found: bad.append(f"{rel}: unexpected BreadcrumbList")
            if navs: bad.append(f"{rel}: unexpected breadcrumb trail")
            continue
        if len(found)!=1:
            bad.append(f"{rel}: expected one BreadcrumbList, found {len(found)}")
            continue
        if len(navs)!=1:
            bad.append(f"{rel}: expected one breadcrumb trail, found {len(navs)}")
            continue
        bc=found[0]
        if bc.get("@context")!="https://schema.org":
            bad.append(f"{rel}: BreadcrumbList @context is {bc.get('@context')}")
        els=bc.get("itemListElement")
        if not isinstance(els, list) or len(els)<2:
            bad.append(f"{rel}: BreadcrumbList needs Home and this page")
            continue
        for i,el in enumerate(els):
            if not isinstance(el, dict) or el.get("@type")!="ListItem":
                bad.append(f"{rel}: crumb {i+1} is not a ListItem")
                continue
            if el.get("position")!=i+1:
                bad.append(f"{rel}: crumb position {el.get('position')} != {i+1}")
            name,item=el.get("name"),el.get("item")
            if not isinstance(name, str) or not name.strip():
                bad.append(f"{rel}: empty crumb name at {i+1}")
            if not isinstance(item, str) or urllib.parse.urlparse(item).scheme!="https":
                bad.append(f"{rel}: crumb {i+1} item is not an absolute https URL ({item})")
                continue
            host=(urllib.parse.urlparse(item).hostname or "").lower()
            if host!=(urllib.parse.urlsplit(BASE).hostname or "").lower():
                bad.append(f"{rel}: crumb URL is not on {BASE} ({item})")
            if item not in by_canon:
                bad.append(f"{rel}: crumb URL is not a built page ({item})")
            elif _url_path(item)!=pages[by_canon[item]]["path"]:
                bad.append(f"{rel}: crumb URL path does not match that page ({item})")
        if els[-1].get("item")!=info["canon"]:
            bad.append(f"{rel}: last crumb {els[-1].get('item')} != canonical {info['canon']}")
        if els[0].get("name")!="Home" or els[0].get("item")!=home:
            bad.append(f"{rel}: first crumb is not the homepage")
        expect=[pages[by_path[ap]]["canon"] for ap in _ancestor_paths(info["path"]) if ap!=home and ap in by_path]
        got=[el.get("item") for el in els[1:-1]]
        if got!=expect:
            bad.append(f"{rel}: parent crumbs {got} != built hubs {expect}")
        if len(els)>2: with_hub+=1
        else:
            parts=[p for p in info["path"].strip("/").split("/") if p]
            pre=_prefix_parts()
            rel_parts=parts[len(pre):] if pre and parts[:len(pre)]==pre else parts
            if len(rel_parts)>=2: skipped_section+=1
        nav=navs[0]
        links=re.findall(r'<a href="([^"]*)">(.*?)</a>', nav)
        current=re.search(r'<span aria-current="page">(.*?)</span>', nav)
        if len(links)!=len(els)-1 or not current:
            bad.append(f"{rel}: visible trail does not match BreadcrumbList ({len(links)} links, current={bool(current)})")
        else:
            if html.unescape(current.group(1))!=els[-1].get("name"):
                bad.append(f"{rel}: visible current crumb does not match the last BreadcrumbList name")
            for (href,label),el in zip(links, els[:-1]):
                if html.unescape(label)!=el.get("name"):
                    bad.append(f"{rel}: visible label {label!r} != {el.get('name')!r}")
                href_path=html.unescape(href)
                if _url_path(el.get("item") or "")!=href_path:
                    bad.append(f"{rel}: visible href {href_path} != {el.get('item')}")
                if not _local_file(href_path):
                    bad.append(f"{rel}: breadcrumb link does not resolve ({href_path})")
        seen.add(info["canon"])
    for loc in locs:
        if loc==home: continue
        if loc not in seen:
            bad.append(f"sitemap URL has no BreadcrumbList: {loc}")
    if len(locs)!=len(set(locs)):
        bad.append("sitemap has duplicate URLs")
    sample=pages.get("gifts/fragrance-gifts-for-teens/index.html")
    if not sample:
        bad.append("missing /gifts/fragrance-gifts-for-teens/ sample page")
    else:
        blocks=[json.loads(s) for s in _ld_scripts(open(f"{OUT}/{sample['rel']}", encoding="utf-8").read())]
        bc=next((b for b in blocks if b.get("@type")=="BreadcrumbList"), None)
        names=[el["name"] for el in bc["itemListElement"]] if bc else []
        if names!=["Home","Gift guides",sample["h1"]]:
            bad.append(f"teens gift trail names {names}")
        elif bc["itemListElement"][-1]["item"]!=sample["canon"]:
            bad.append("teens gift trail last item is not the canonical")
        elif bc["itemListElement"][1]["item"]!=pages[by_path["/gifts/"]]["canon"]:
            bad.append("teens gift trail does not link the /gifts/ hub")
    if bad:
        print("breadcrumb check failed:")
        for line in bad[:40]: print(" ", line)
        raise SystemExit(f"breadcrumb check failed ({len(bad)} problems)")
    nonhome=len(locs)-(1 if home in locs else 0)
    print(f"breadcrumb audit: sitemap {len(locs)} urls, {nonhome} non-home each with one BreadcrumbList; {len(seen)} html trails ({with_hub} via a hub, {skipped_section} sections with no hub skipped); homepage and 404 have none")
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
def _attr(attrs, name):
    m=re.search(rf'{name}\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', attrs, re.I)
    return html.unescape((m.group(1) if m.group(1) is not None else m.group(2)) if m else "")
def _ld_images(node):
    img=node.get("image") if isinstance(node, dict) else None
    if isinstance(img, str): return [img]
    if isinstance(img, list):
        out=[]
        for x in img:
            if isinstance(x, str): out.append(x)
            elif isinstance(x, dict) and x.get("url"): out.append(x["url"])
        return out
    if isinstance(img, dict) and img.get("url"): return [img["url"]]
    return []
def _walk_ld(node, products):
    if isinstance(node, dict):
        if node.get("@type")=="Product": products.append(node)
        for v in node.values(): _walk_ld(v, products)
    elif isinstance(node, list):
        for v in node: _walk_ld(v, products)
def _local_path(href):
    """Site path for an internal URL, or None when it is external or a tracking URL. Does not fetch."""
    href=html.unescape(href or "").strip()
    if not href or href.startswith(("#","mailto:","tel:","javascript:","data:")): return None
    if links.is_tracking_url(href) or links.is_internal_redirect(href): return None
    parsed=urllib.parse.urlparse(href)
    if parsed.scheme in ("http","https"):
        host=(parsed.hostname or "").lower()
        if host not in ("scentdealsdaily.com","www.scentdealsdaily.com"): return None
        path=urllib.parse.unquote(parsed.path or "/")
    elif parsed.scheme: return None
    else:
        path=urllib.parse.unquote(parsed.path or href)
    path=path.split("?")[0].split("#")[0]
    if PREFIX and path.startswith(PREFIX+"/"): path=path[len(PREFIX):] or "/"
    if not path.startswith("/"): path="/"+path
    return path
def _local_file(path):
    rel=path.lstrip("/")
    cands=[os.path.join(OUT, rel)] if rel else [os.path.join(OUT, "index.html")]
    if rel.endswith("/"): cands.append(os.path.join(OUT, rel, "index.html"))
    elif rel: cands.append(os.path.join(OUT, rel, "index.html"))
    return next((c for c in cands if os.path.isfile(c)), None)
def _photo_roundup(rel):
    """Pages whose product cards must keep a real img. A missing image fails the build."""
    return rel.startswith("gifts/") or rel.startswith("black-friday-fragrance-deals/")
def audit_cards_links_jsonld():
    """Fail when a product card has no image. Warn when the only image is the neutral placeholder.
    Parse every JSON-LD block and resolve internal links on disk. Never request a tracking URL."""
    bad=[]
    broken=[]
    jsonld_blocks=0
    card_re=re.compile(r'<article class="card">(.*?)</article>', re.S)
    img_re=re.compile(r"<img\b([^>]*)>", re.I)
    href_re=re.compile(r"""<(?:a|link)\b([^>]*?)href\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
    gift_rows=[]
    cards=0
    for dirpath, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"): continue
            path=os.path.join(dirpath, fn)
            rel=os.path.relpath(path, OUT).replace(os.sep, "/")
            text=open(path, encoding="utf-8").read()
            page_dir=os.path.dirname(rel)
            for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
                jsonld_blocks+=1
                try: data=json.loads(raw)
                except json.JSONDecodeError as ex:
                    bad.append(f"{rel}: JSON-LD did not parse ({ex})")
                    continue
                products=[]
                _walk_ld(data, products)
                for product in products:
                    for img in _ld_images(product):
                        host=(urllib.parse.urlparse(img).hostname or "").lower()
                        if "macys" in host:
                            bad.append(f"{rel}: JSON-LD image is from macys.com ({product.get('name')})")
            found=card_re.findall(text)
            card_srcs=[]
            placeholders=0
            for body in found:
                cards+=1
                ims=img_re.findall(body)
                if not ims:
                    bad.append(f"{rel}: product card rendered with no img")
                    continue
                attrs=ims[0]
                src=_attr(attrs, "src"); alt=_attr(attrs, "alt")
                if not src: bad.append(f"{rel}: product card img has an empty src")
                if not alt: bad.append(f"{rel}: product card img has an empty alt")
                if not _attr(attrs, "width") or not _attr(attrs, "height"):
                    bad.append(f"{rel}: product card img missing width or height")
                if not re.search(r"decoding\s*=\s*[\"']async[\"']", attrs, re.I):
                    bad.append(f"{rel}: product card img missing decoding=async")
                lazy=re.search(r"loading\s*=\s*[\"']lazy[\"']", attrs, re.I)
                eager=re.search(r"fetchpriority\s*=\s*[\"']high[\"']", attrs, re.I)
                if not lazy and not eager:
                    bad.append(f"{rel}: product card img missing loading=lazy")
                host=(urllib.parse.urlparse(src).hostname or "").lower()
                if "macys" in host or "macys.com" in src.lower():
                    bad.append(f"{rel}: product card uses a macys.com image")
                if src.startswith("data:"): placeholders+=1
                elif src.startswith(("http://","https://")): card_srcs.append(src)
                elif src.startswith("/"):
                    if not _local_file(src.split("?")[0].split("#")[0]):
                        bad.append(f"{rel}: product card image file missing ({src[:80]})")
                if _photo_roundup(rel) and not lazy:
                    bad.append(f"{rel}: gift card image must use loading=lazy")
            if _photo_roundup(rel) and found:
                # ItemList products only. FAQPage blocks on the same page are not products.
                item_imgs=[]
                item_n=0
                bare=0
                for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
                    try: data=json.loads(raw)
                    except json.JSONDecodeError: continue
                    lists=[]
                    def walk_lists(node):
                        if isinstance(node, dict):
                            if node.get("@type")=="ItemList": lists.append(node)
                            for v in node.values(): walk_lists(v)
                        elif isinstance(node, list):
                            for v in node: walk_lists(v)
                    walk_lists(data)
                    for lst in lists:
                        for el in lst.get("itemListElement") or []:
                            item=(el.get("item") if isinstance(el, dict) else None) or {}
                            if item.get("@type")!="Product": continue
                            item_n+=1
                            imgs=_ld_images(item)
                            if imgs: item_imgs.extend(imgs)
                            else: bare+=1
                missing=[s for s in card_srcs if s not in set(item_imgs)]
                if missing:
                    bad.append(f"{rel}: {len(missing)} card photo(s) missing from ItemList JSON-LD")
                if bare!=placeholders:
                    bad.append(f"{rel}: {bare} ItemList products lack an image, {placeholders} cards use the placeholder")
                if item_n and len(found)<item_n:
                    bad.append(f"{rel}: {len(found)} cards for {item_n} ItemList products")
                gift_rows.append((rel, len(found), len(found)-placeholders, placeholders))
            for tag, h1, h2 in href_re.findall(text):
                href=h1 or h2
                local=_local_path(href)
                if local is None:
                    # Relative links stay on this page's directory.
                    raw_href=html.unescape(href or "").strip()
                    if raw_href and not raw_href.startswith(("#","mailto:","tel:","javascript:","data:","http://","https://","/")) and not links.is_tracking_url(raw_href):
                        joined=os.path.normpath(os.path.join("/"+page_dir, raw_href.split("?")[0].split("#")[0]))
                        local=joined if joined.startswith("/") else "/"+joined
                if not local: continue
                if not _local_file(local):
                    broken.append(f"{rel}: {local}")
    if MISSING_PHOTOS:
        print("WARNING: product cards with no retailer image. A neutral placeholder is shown. Do not invent a photo.")
        for row in MISSING_PHOTOS:
            size=f" {row['size']}" if row["size"] else ""
            print(f"WARNING: missing image: {row['label']}{'' if row['size'] and row['size'].lower() in row['label'].lower() else size}")
    else:
        print("product images: every rendered product has a retailer image; no placeholders")
    if broken:
        bad.extend(f"broken internal link {line}" for line in broken)
    if bad:
        print("WARNING: product-card image check failed:")
        for line in bad[:60]: print(" ", line)
        raise SystemExit(f"product-card image check failed ({len(bad)} problems)")
    print(f"product-card image check: {cards} cards, all have an image; {jsonld_blocks} JSON-LD blocks parsed; {len(broken)} broken internal links")
    for rel, n, photos, ph in sorted(gift_rows):
        print(f"  /{os.path.dirname(rel) or 'gifts'}/: {n} cards, {photos} retailer photos, {ph} placeholders")
def audit_share_meta():
    """Every HTML page has one absolute og:image on this host, and og:url equals the canonical."""
    bad=[]
    specific=[]
    defaulted=[]
    htmls=0
    prop_re=re.compile(r'<meta\s+property="([^"]+)"\s+content="([^"]*)"', re.I)
    name_re=re.compile(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"', re.I)
    canon_re=re.compile(r'<link\s+rel="canonical"\s+href="([^"]*)"', re.I)
    title_re=re.compile(r"<title>(.*?)</title>", re.S)
    host=(urllib.parse.urlsplit(BASE).hostname or "").lower()
    for dirpath, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"): continue
            htmls+=1
            path=os.path.join(dirpath, fn)
            rel=os.path.relpath(path, OUT).replace(os.sep, "/")
            text=open(path, encoding="utf-8").read()
            head=text.split("</head>",1)[0]
            props={}; names={}
            for k,v in prop_re.findall(head): props.setdefault(k, []).append(html.unescape(v))
            for k,v in name_re.findall(head): names.setdefault(k, []).append(html.unescape(v))
            def one(bag, key):
                vals=bag.get(key) or []
                if len(vals)!=1:
                    bad.append(f"{rel}: expected one {key}, found {len(vals)}")
                    return None
                return vals[0]
            og_type,og_site=one(props,"og:type"),one(props,"og:site_name")
            og_title,og_desc=one(props,"og:title"),one(props,"og:description")
            og_url,og_img=one(props,"og:url"),one(props,"og:image")
            tw_card,tw_title=one(names,"twitter:card"),one(names,"twitter:title")
            tw_desc,tw_img=one(names,"twitter:description"),one(names,"twitter:image")
            canon_m=canon_re.search(head)
            canon=html.unescape(canon_m.group(1)) if canon_m else ""
            title_m=title_re.search(head)
            title=html.unescape(title_m.group(1)) if title_m else ""
            desc_vals=names.get("description") or []
            desc=desc_vals[0] if desc_vals else ""
            if not canon: bad.append(f"{rel}: missing canonical")
            if og_url and canon and og_url!=canon: bad.append(f"{rel}: og:url {og_url} != canonical {canon}")
            if og_type and og_type!="website": bad.append(f"{rel}: og:type {og_type}")
            if og_site and og_site!=NAME: bad.append(f"{rel}: og:site_name {og_site}")
            if og_title is not None and title and og_title!=title: bad.append(f"{rel}: og:title does not match <title>")
            if og_desc is not None and desc and og_desc!=desc: bad.append(f"{rel}: og:description does not match meta description")
            if tw_card and tw_card!="summary_large_image": bad.append(f"{rel}: twitter:card {tw_card}")
            if tw_title and og_title and tw_title!=og_title: bad.append(f"{rel}: twitter:title does not match og:title")
            if tw_desc and og_desc and tw_desc!=og_desc: bad.append(f"{rel}: twitter:description does not match og:description")
            if tw_img and og_img and tw_img!=og_img: bad.append(f"{rel}: twitter:image does not match og:image")
            if not og_img: continue
            parsed=urllib.parse.urlparse(og_img)
            if parsed.scheme!="https" or (parsed.hostname or "").lower()!=host:
                bad.append(f"{rel}: og:image is not an absolute https://{host} URL ({og_img})")
            elif not _local_file(parsed.path):
                bad.append(f"{rel}: og:image file missing ({parsed.path})")
            else:
                page_path=urllib.parse.urlparse(canon).path if canon else "/"+rel
                if parsed.path==DEFAULT_SHARE:
                    defaulted.append(page_path)
                else:
                    specific.append((page_path, parsed.path))
    if bad:
        print("share metadata check failed:")
        for line in bad[:40]: print(" ", line)
        raise SystemExit(f"share metadata check failed ({len(bad)} problems)")
    print(f"share metadata: {htmls} pages, {len(specific)} page-specific images, {len(defaulted)} default images")
    for url, img in sorted(specific):
        print(f"  specific {url} -> {img}")
def audit_gift_pins():
    """Every sitemap /gifts/ URL has its own 1000x1500 pin. Other pages keep their image."""
    from PIL import Image
    bad=[]
    prop_re=re.compile(r'<meta\s+property="og:image"\s+content="([^"]*)"', re.I)
    def og_of(rel):
        text=open(os.path.join(OUT, rel), encoding="utf-8").read().split("</head>",1)[0]
        vals=[html.unescape(v) for v in prop_re.findall(text)]
        if len(vals)!=1:
            bad.append(f"{rel}: expected one og:image, found {len(vals)}")
            return None
        return vals[0]
    def rel_for(loc):
        path=urllib.parse.urlparse(loc).path
        if PREFIX and path.startswith(PREFIX+"/"): path=path[len(PREFIX):] or "/"
        if not path.startswith("/"): path="/"+path
        rel=path.strip("/")
        return (rel+"/index.html") if path.endswith("/") or not rel else rel
    sitemap=open(f"{OUT}/sitemap.xml", encoding="utf-8").read()
    locs=re.findall(r"<loc>([^<]+)</loc>", sitemap)
    gift_locs=[u for u in locs if urllib.parse.urlparse(u).path.rstrip("/").endswith("/gifts") or "/gifts/" in urllib.parse.urlparse(u).path]
    seen={}; hashes={}; rows=[]
    for loc in gift_locs:
        rel=rel_for(loc)
        og=og_of(rel)
        if not og: continue
        parsed=urllib.parse.urlparse(og)
        slug="gifts" if urllib.parse.urlparse(loc).path.rstrip("/").endswith("/gifts") else urllib.parse.urlparse(loc).path.rstrip("/").split("/")[-1]
        expect=f"/media/pins/{slug}.png"
        if not parsed.path.endswith(expect):
            bad.append(f"{loc}: og:image {parsed.path} is not {expect}")
        local=_local_file(parsed.path)
        if not local:
            bad.append(f"{loc}: og:image file missing ({parsed.path})")
            continue
        if Image.open(local).size!=(1000,1500):
            bad.append(f"{loc}: og:image is {Image.open(local).size}, expected 1000x1500")
        if og in seen:
            bad.append(f"{loc}: og:image also used by {seen[og]}")
        seen[og]=loc
        digest=_sha256_file(local)
        if digest in hashes:
            bad.append(f"{loc}: pin pixels match {hashes[digest]}")
        hashes[digest]=loc
        base=os.path.basename(parsed.path)
        if base in giftpins.LEGACY or parsed.path.endswith(DEFAULT_SHARE):
            bad.append(f"{loc}: still using a shared image ({parsed.path})")
        rows.append((loc, og))
    built=[]
    for dirpath,_,files in os.walk(os.path.join(OUT,"gifts")):
        for fn in files:
            if fn.endswith(".html"):
                built.append(os.path.relpath(os.path.join(dirpath,fn), OUT).replace(os.sep,"/"))
    sitemap_rels={rel_for(u) for u in gift_locs}
    for rel in built:
        if rel not in sitemap_rels:
            bad.append(f"{rel}: gift page missing from the sitemap")
    for dirpath,_,files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"): continue
            rel=os.path.relpath(os.path.join(dirpath,fn), OUT).replace(os.sep,"/")
            if rel.startswith("gifts/"): continue
            og=og_of(rel)
            if not og: continue
            if rel=="black-friday-fragrance-deals/index.html":
                if not og.endswith("/media/pins/holiday-fragrance-gifts.png"):
                    bad.append(f"{rel}: image changed ({og})")
            elif not og.endswith(DEFAULT_SHARE):
                bad.append(f"{rel}: non-gift og:image changed ({og})")
    if bad:
        print("gift pin check failed:")
        for line in bad[:40]: print(" ", line)
        raise SystemExit(f"gift pin check failed ({len(bad)} problems)")
    print(f"gift pins: {len(rows)} /gifts/ URLs, each image distinct and 1000x1500")
    for loc, og in rows:
        print(f"  {loc} -> {og}")
apply_breadcrumbs()
audit_breadcrumbs()
audit_affiliate_output()
audit_cards_links_jsonld()
audit_share_meta()
audit_gift_pins()
