#!/usr/bin/env python3
"""Cache retailer product photos under site/media/products/{slug}.jpg.

Pinterest rejects images hosted on fragranceshop.com ("this site doesn't allow
pins to be saved"). Gift-guide pins already live on this host; deal pins need
the same. This copies each deal's existing retailer photo (never macys.com,
never an affiliate tracking URL) into site/media/products so Buffer can use
https://scentdealsdaily.com/media/products/{frag_slug}.jpg.

Existing files are left byte-for-byte (the build already refuses to change
other media). A failed download is a warning, not a build failure.
"""
from __future__ import annotations

import io
import os
import urllib.error
import urllib.request

import links

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("product pin images need Pillow. Install it with: python3 -m pip install pillow") from exc

UA = "ScentDealsDaily/1.0 (+https://scentdealsdaily.com)"
MAX_BYTES = 8 * 1024 * 1024
TIMEOUT = 25


def _url_ok(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    if links.is_tracking_url(url) or links.is_internal_redirect(url):
        return False
    return True


def _fetch_urllib(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        final = resp.geturl()
        if not _url_ok(final):
            raise ValueError("image request redirected to a tracking URL")
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("image larger than 8MB")
    if not data:
        raise ValueError("empty image body")
    return data


def _fetch_curl(url: str) -> bytes:
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [
                "curl", "-fsSL", "--retry", "3", "--retry-all-errors",
                "--max-time", str(TIMEOUT + 15),
                "-A", "Mozilla/5.0 (compatible; ScentDealsDaily/1.0; +https://scentdealsdaily.com)",
                "-H", "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "-o", tmp_path, url,
            ],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "curl failed").strip()
            raise ValueError(f"curl failed: {err[-200:]}")
        with open(tmp_path, "rb") as f:
            data = f.read()
        if len(data) > MAX_BYTES:
            raise ValueError("image larger than 8MB")
        if not data:
            raise ValueError("empty image body")
        return data
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _fetch(url: str) -> bytes:
    if not _url_ok(url):
        raise ValueError("refusing tracking or empty image URL")
    try:
        return _fetch_urllib(url)
    except Exception:
        return _fetch_curl(url)


def _to_jpeg(data: bytes) -> bytes:
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    if min(im.size) < 200:
        raise ValueError(f"image too small: {im.size}")
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=90, optimize=True)
    return out.getvalue()


def cache(deals, dest, slug_of, image_of) -> dict:
    """Write missing {slug}.jpg files into dest. Returns counts."""
    os.makedirs(dest, exist_ok=True)
    seen = set()
    stats = {"cached": 0, "downloaded": 0, "failed": 0, "skipped": 0}
    for deal in deals or []:
        if not isinstance(deal, dict):
            continue
        if not deal.get("brand") or not deal.get("name"):
            stats["skipped"] += 1
            continue
        slug = slug_of(deal)
        if not slug or slug in seen:
            if slug in seen:
                pass  # same fragrance slug, one file is enough
            else:
                stats["skipped"] += 1
            continue
        seen.add(slug)
        path = os.path.join(dest, f"{slug}.jpg")
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            stats["cached"] += 1
            continue
        url = image_of(deal)
        if not url:
            stats["skipped"] += 1
            continue
        try:
            jpeg = _to_jpeg(_fetch(url))
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(jpeg)
            os.replace(tmp, path)
            stats["downloaded"] += 1
            print(f"product pin image: saved {os.path.basename(path)}")
        except Exception as exc:
            stats["failed"] += 1
            print(f"WARNING: product pin image failed for {slug}: {exc}")
    print(
        "product pin images: "
        f"{stats['cached']} already cached, {stats['downloaded']} downloaded, "
        f"{stats['failed']} failed, {stats['skipped']} skipped"
    )
    return stats


if __name__ == "__main__":
    import json
    import sys

    # Standalone: reuse slug and image rules from build without running the render.
    # Importing build.py wipes site/, so the helpers are copied here only as a runner.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    def slug(s):
        import re
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    def frag_slug(d):
        base = slug(f"{d['brand']} {d['name']}")
        if d.get("url_size"):
            return slug(f"{d['brand']} {d['name']} {d.get('size') or ''}")
        return base

    def image_of(d):
        url = (d.get("image") or "").strip() if isinstance(d.get("image"), str) else ""
        if not url.startswith(("http://", "https://")):
            return ""
        host = (links.host_of(url) or "")
        if not host or "macys" in host:
            return ""
        return url

    data = json.load(open(os.path.join(root, "data/deals.json")))
    dest = os.path.join(root, "site/media/products")
    cache(data.get("deals"), dest, frag_slug, image_of)
