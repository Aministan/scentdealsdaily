# ScentDealsDaily (v1)
Authentic designer fragrance deals + dupes directory. Static site, $0 hosting.
- `data/config.json` – which products to track (Perfumania handles) + curated dupe pairs w/ sources
- `scripts/refresh.py` – (retries 429s with backoff; keeps the last good deals.json if >20% of fetches fail) re-checks price/compare-at/stock via Perfumania's public Shopify JSON, then the same bottle at FragranceShop when the size and concentration can be priced live, drops dead/<15%-off deals → `data/deals.json`
- `data/config.json` `hubs` – dupe comparison hubs (/dupes/<slug>/) built from dupes whose original matches; `/best/*-under-50/` roundups are generated from deals.json automatically
- `scripts/build.py` – renders `site/` (homepage, /dupes, /men, /women, /unisex, /brands/*, /sponsor, /disclosure, sitemap.xml, robots.txt, llms.txt, deals.json, JSON-LD ItemList/Product/FAQ)
- `scripts/pins.py` – during the build, draws a 1000×1500 pin for each `/gifts/` page (Pillow; fonts in `scripts/fonts/`)
- `.github/workflows/daily.yml` – daily refresh + GitHub Pages deploy
Local: `python3 -m pip install 'Pillow>=10.4,<12' && python3 scripts/refresh.py && python3 scripts/build.py && (cd site && python3 -m http.server)`
Env: SITE_URL, PATH_PREFIX, NEWSLETTER_ENDPOINT (e.g. a free Buttondown/Beehiiv/Formspree form URL).
