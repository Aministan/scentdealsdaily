#!/usr/bin/env python3
"""Ping IndexNow (Bing/Yandex/Seznam; Google ignores it) with every sitemap URL. Run after deploy: SITE_URL=... python3 scripts/indexnow.py"""
import os,re,json,hashlib,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY=hashlib.md5(b"scentdealsdaily-indexnow").hexdigest()
urls=re.findall(r"<loc>([^<]+)</loc>",open(f"{ROOT}/site/sitemap.xml").read())
host=urls[0].split("/")[2]; pre=os.environ.get("PATH_PREFIX","")
body=json.dumps({"host":host,"key":KEY,"keyLocation":f"https://{host}{pre}/{KEY}.txt","urlList":urls}).encode()
r=urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/indexnow",data=body,headers={"Content-Type":"application/json"}))
print(r.status,len(urls),"urls")
