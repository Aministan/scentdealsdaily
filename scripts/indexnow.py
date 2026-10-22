#!/usr/bin/env python3
"""Ping IndexNow with sitemap URLs (or URLs passed as args). Run after deploy: PATH_PREFIX=/scentdealsdaily python3 scripts/indexnow.py [url ...]
Bing/api.indexnow.org currently answer 403 UserForbiddedToAccessSite for aministan.github.io (they want ownership of the bare
github.io host, which a project page can't prove), so we also ping Yandex directly, which accepts the path-scoped key. Never fails the build."""
import os,re,sys,json,hashlib,urllib.request,urllib.error
import links
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY=hashlib.md5(b"scentdealsdaily-indexnow").hexdigest()
urls=sys.argv[1:] or re.findall(r"<loc>([^<]+)</loc>",open(f"{ROOT}/site/sitemap.xml").read())
urls=[re.sub(r"^(https?://[^/]+)",lambda m:m.group(1).lower(),u) for u in urls]  # Yandex answers 422 "Invalid key location" for a mixed-case host
urls=[u for u in urls if not links.is_tracking_url(u) and not links.is_internal_redirect(u)]
host=urls[0].split("/")[2]; pre=os.environ.get("PATH_PREFIX","")
body=json.dumps({"host":host,"key":KEY,"keyLocation":f"https://{host}{pre}/{KEY}.txt","urlList":urls}).encode()
for ep in ["https://api.indexnow.org/indexnow","https://yandex.com/indexnow"]:
    try:
        r=urllib.request.urlopen(urllib.request.Request(ep,data=body,headers={"Content-Type":"application/json; charset=utf-8"}),timeout=30)
        print(ep,r.status,len(urls),"urls")
    except urllib.error.HTTPError as e:
        print(ep,e.code,e.read()[:200].decode("utf-8","replace"))
    except Exception as e:
        print(ep,"error",e)
