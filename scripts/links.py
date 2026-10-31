#!/usr/bin/env python3
"""Affiliate URL rules for ScentDealsDaily.

Automation may validate a tracking link by string format only. It must never
request a Commission Junction (or other network) click URL, or an internal
/go /out /redirect /r path that forwards to one. A check fetches the plain
retailer product URL instead (perfumania.com, fragranceshop.com, fragrancenet.com,
and the like).
"""
import re
import urllib.parse

# Hosts that record an affiliate click when requested.
TRACKING_DOMAINS = (
    "anrdoezrs.net",
    "jdoqocy.com",
    "tkqlhce.com",
    "dpbolvw.net",
    "kqzyfj.com",
    "emjcd.com",
    "awin1.com",
    "click.linksynergy.com",
    "linksynergy.com",
)
# Internal paths that must not be fetched by crawlers or by our own scripts.
REDIRECT_PREFIXES = ("/go/", "/out/", "/redirect/", "/r/")
_CJ_CLICK = re.compile(r"/click-\d+-\d+")
_OUR_HOSTS = ("scentdealsdaily.com", "github.io")


def host_of(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def host_is(host, domain):
    host = (host or "").lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def is_tracking_host(host):
    return any(host_is(host, domain) for domain in TRACKING_DOMAINS)


def is_tracking_url(url):
    """True when requesting this string would hit a tracking domain."""
    if not isinstance(url, str) or not url:
        return False
    if is_tracking_host(host_of(url)):
        return True
    low = url.lower()
    return any(domain in low for domain in TRACKING_DOMAINS)


def is_redirect_path(path):
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    for prefix in REDIRECT_PREFIXES:
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return True
    return False


def is_internal_redirect(url):
    """Site redirect/go links. Requesting them forwards into a tracking URL."""
    if not isinstance(url, str) or not url:
        return False
    parsed = urllib.parse.urlparse(url)
    if not is_redirect_path(parsed.path):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return True
    return any(host == item or host.endswith("." + item) for item in _OUR_HOSTS)


def _http_urls(text):
    found = []
    for match in re.finditer(r"https?://[^\s\"'<>]+", text or ""):
        found.append(match.group(0).rstrip(").,]"))
    return found


def retailer_url(url):
    """Plain product URL. Tracking and internal redirect links unwrap to it.

    Returns the original URL when it is already a plain URL. Returns None when
    a tracking or redirect URL has no plain retailer target.
    """
    if not isinstance(url, str) or not url:
        return url
    if not is_tracking_url(url) and not is_internal_redirect(url):
        return url
    candidates = []
    try:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    except Exception:
        query = {}
    for key in ("url", "murl", "u", "dest", "destination", "redirect"):
        candidates.extend(query.get(key) or [])
    decoded = urllib.parse.unquote(url)
    candidates.extend(_http_urls(decoded))
    plain = []
    for candidate in candidates:
        candidate = (candidate or "").strip()
        if not candidate.startswith(("http://", "https://")):
            continue
        if is_tracking_url(candidate) or is_internal_redirect(candidate):
            continue
        plain.append(candidate)
    if not plain:
        return None

    def rank(item):
        host = host_of(item)
        if host_is(host, "perfumania.com") or host_is(host, "fragranceshop.com") or host_is(host, "fragrancenet.com"):
            return 0
        return 1

    return sorted(plain, key=rank)[0]


def safe_request_url(url):
    """URL our scripts may GET. Never a tracking or internal redirect URL."""
    if not isinstance(url, str) or not url:
        return url
    if is_tracking_url(url) or is_internal_redirect(url):
        plain = retailer_url(url)
        if plain and not is_tracking_url(plain) and not is_internal_redirect(plain):
            return plain
        return None
    return url


def affiliate_link_ok(url):
    """String-format check for a click URL. Does not request it."""
    if not isinstance(url, str) or not url:
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        return False
    host = host_of(url)
    if not is_tracking_host(host):
        return False
    cj = any(host_is(host, domain) for domain in (
        "anrdoezrs.net", "jdoqocy.com", "tkqlhce.com", "dpbolvw.net", "kqzyfj.com", "emjcd.com",
    ))
    if cj and not _CJ_CLICK.search(parsed.path or ""):
        return False
    if not (parsed.path or "/").strip("/"):
        return False
    query = urllib.parse.parse_qs(parsed.query)
    inner = (query.get("url") or query.get("murl") or [None])[0]
    if host_is(host, "linksynergy.com"):
        # Rakuten Advertising deep link for FragranceNet. Checked as text only.
        if (parsed.path or "").rstrip("/") != "/deeplink":
            return False
        ident = (query.get("id") or [None])[0]
        mid = (query.get("mid") or [None])[0]
        if ident != "cED93qTW*cI" or mid != "216":
            return False
        if not inner:
            return False
        if not host_is(host_of(inner), "fragrancenet.com"):
            return False
    if inner is None:
        return True
    inner_parsed = urllib.parse.urlparse(inner)
    if inner_parsed.scheme not in ("http", "https"):
        return False
    if is_tracking_url(inner) or is_internal_redirect(inner):
        return False
    return bool(host_of(inner))
