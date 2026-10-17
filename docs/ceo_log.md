# ScentDealsDaily CEO log

## 2026-10-16 (Fri) — daily optimization pass (Grok Bot)

**Refresh status:** today's scheduled `daily-refresh` run (run 38923372351, started 11:22 AM ET, ~4h after the 7:17 AM cron because GitHub delayed it) finished "success" and deployed, but it was degraded: Perfumania answered **HTTP 429 Too Many Requests** halfway through, so 13 compare-deals and 13/15 dupe prices were silently dropped (site went from ~37 to 28 deals, 2/15 dupes priced). IndexNow step also failed (403).

**Fixes**
- `scripts/refresh.py`: retries 429/5xx with Retry-After / exponential backoff, 1.2 s pause between products (`REFRESH_PAUSE`), and a degraded-run guard (if >20% of fetches still fail, keep the last verified deals.json if it's <48h old instead of publishing a half-empty site). Gender detection now also reads the product handle (CK One is tagged GENDER_Women but is unisex).
- `scripts/indexnow.py`: pings api.indexnow.org and Yandex separately, prints each response, never fails the build. Bing/api.indexnow.org return `403 UserForbiddedToAccessSite` for aministan.github.io (they want ownership of the bare github.io host, which a project page can't prove). Yandex accepts (202).
- Local refresh with the fix: 42 live deals, 12/15 dupes priced, 0/120 fetch failures.

**Deals added (5, all live-verified Oct 16 at Perfumania; 15%+ off)**
- Giorgio Armani Stronger With You Intensely 1.7 oz: $86.95 vs Ulta $105.00 (Muse.ai find; Ulta price re-verified live) = 17% below Ulta.
- Elizabeth Arden Green Tea Scent 3.4 oz: $31.95 vs $51.00 listed (-37%); Muse.ai's Ulta comp $52.00 for 3.3 oz re-verified live.
- Juicy Couture Peace Love & Juicy Couture 3.4 oz: $28.95 vs $96.00 (-70%).
- Calvin Klein CK One 1.7 oz: $24.95 vs $59.00 (-58%), unisex.
- Hugo Boss Boss In Motion 3.0 oz: $44.95 vs $76.00 (-41%).
- 13 previously tracked compare-deals that the 429s dropped are back (Versace Eros, Eros Flame, Bright Crystal Absolu, Dylan Blue Pour Femme; Valentino Born in Roma x3; JPG Le Beau; Lancôme La Vie Est Belle; etc.).

**Dropped / skipped**
- Dropped by refresh (no longer 15%+ off, or unavailable): Hermès H24, Ariana Grande Sweet Like Candy, Montblanc Legend Spirit, Ralph Lauren Romance, Gucci Bloom (<15% below Ulta), Lancôme Idôle (<15% below Ulta).
- Muse.ai items skipped: all eBay listings (marketplace sellers), Walmart/PerfumesAmerica (counterfeit-review flag), Nordstrom Rack items (no Perfumania match, or Rack is cheaper than Perfumania so a Perfumania "deal" would mislead: CK Obsession women 3.4 Rack $49.97 vs Perfumania $79.95; D&G The One 2.5 Rack $99.97 vs $136.95; Polo Red 4.2 Rack $84.97 vs $96.95), Ari 1.0 oz (Perfumania doesn't stock that size), Viva La Juicy original, Sol de Janeiro Cheirosa 62 EDP, gift and mini sets (not on Perfumania).

**New pages (data-driven in build.py + config `hubs`, so they survive the daily rebuild)**
- https://aministan.github.io/scentdealsdaily/best/cologne-deals-under-50/
- https://aministan.github.io/scentdealsdaily/best/perfume-deals-under-50/
- https://aministan.github.io/scentdealsdaily/dupes/creed-dupes/
- https://aministan.github.io/scentdealsdaily/dupes/baccarat-rouge-540-dupes/
- https://aministan.github.io/scentdealsdaily/dupes/kilian-angels-share-dupes/
Each has ItemList (Product/Offer) and FAQPage JSON-LD, a price-per-ounce table, quick picks computed from deals.json, and links in from the homepage, men/women/unisex, dupes index, dupe pages and fragrance pages (9–13 inbound links each).

**Titles/meta improved**
- Fragrance pages: no more doubled brand ("Azzaro Azzaro Cologne" -> "Azzaro Cologne", same for Coach, Versace Pour Homme, Bvlgari Man). URLs unchanged. The FAQ "save per ounce" now gives a real per-ounce price.
- Men/Women/Unisex: title shows max % off; description shows count, lowest price and brands.
- Brand pages: "{Brand} Perfume & Cologne Deals: Up to N% Off Today", with count, lowest price and products in the description.
- Brands index and disclosure: real descriptions instead of a single generic line.
- Dupe pages: description now carries the scent profile and today's verified price.

**Checks:** 89 pages, all JSON-LD parses, 0 broken internal links out of 1,546, no duplicate titles, sitemap.xml and llms.txt regenerated (llms.txt has a new "Buying guides & dupe comparisons" section).

**Open issues**
- Bing IndexNow refuses github.io project sites. A custom domain (e.g. scentdealsdaily.com) would fix it; verifying the site in Bing Webmaster Tools (it can import from Google Search Console) may also help. Yandex accepts the pings already.
- No affiliate click or sale data source is connected to the box (CJ isn't checked by design). The hits.sh visitor badge is the only traffic signal.
- 3 dupes have no Perfumania listing (Club de Nuit Iconic, Club de Nuit Woman, Al Nashama Caprice), so they stay unpriced.
- There are two Lancôme brand pages (/brands/lanc-me/ and /brands/lancome/) because Perfumania uses both vendor spellings.

**Deploy (added after push, not yet committed):** commit 747efb6 was pushed to main at 11:43 AM ET. The push-triggered daily-refresh run 38926299149 passed both build and deploy by 11:46 AM ET. CI refresh with the 429 fix: 42 live deals, 12/15 dupes priced. It hit 4 rate-limit retries, and all of them recovered. The bot then committed 4169616 "daily refresh". All 5 new pages and 5 new deal pages return 200 live. IndexNow: a manual ping of 16 new/changed URLs got Yandex 200 and api.indexnow.org/Bing 403. Inside CI the Yandex ping returned 422 "Invalid key location", while the same key worked from the box. That needs a look.
Box note: /workspace/scentdeals was a stale local repo with no git remote and different history from GitHub (it lacked the CJ link wrapping and Google verification commits). It's been moved to /workspace/scentdeals.stale-local-20261016 and replaced with a fresh clone of GitHub main.

## 2026-10-17 (Sat) — daily optimization pass (Grok Bot)

**Refresh status:** site live (200). Today's daily-refresh committed a76acd6 at 10:18 AM ET (data stamped 10:12 AM ET): 42 live deals, 12/15 dupes priced, 26 deals now pointing at FragranceShop where it's cheaper.

**Bug fixed (15% floor):** when FragranceShop won the price, `fragranceshop._apply` recomputed % off against FragranceShop's own compare-at only, so Lancôme La Vie Est Belle 1.0 oz went live at **13% off** (below our 15% rule). Now: if the store's own compare-at gives <15%, it falls back to the highest authorized third-party price for the same bottle (Ulta via Muse.ai, labeled), and `refresh.py` drops anything still under 15% (both after the store merge and right before writing deals.json). La Vie Est Belle becomes $70.95 vs Ulta $95 (-25%), labeled "below the Ulta price".

**Muse.ai deals:** muse_deals.json unchanged since Oct 15 (56 rows). All usable Ulta comps are already wired as compare-deals; the rest stay skipped for the same reasons as yesterday (eBay/marketplace sellers, Walmart PerfumesAmerica flag, sets/minis not stocked, Nordstrom Rack cheaper than our affiliate stores). No new deals merged, no prices invented.

**New pages (5, data-driven so they survive the rebuild)**
- /best/fragrance-deals-under-30/ (13 picks today)
- /best/luxury-fragrance-deals/ ($120+ list price, 10 picks)
- /vs/versace-eros-vs-eros-flame/
- /vs/valentino-uomo-born-in-roma-vs-intense/
- /vs/ck-one-vs-ck-everyone/
Roundups reuse the ItemList(Product/Offer)+FAQPage template (now parameterized by scope). Vs pages (config `vs`) have two Product/Offer blocks + FAQPage, side-by-side price/size/per-oz/concentration/key-notes table, computed "which to buy" bullets, and only render while both bottles are live deals. Linked from homepage, gender pages, both fragrance pages and each other.

**Titles/meta/UX**
- Fragrance pages: size tidied in title/H1/meta ("3.4 oz." / "3.3  oz." -> "3.4 oz"); meta names the comparison store when the "was" price is another retailer's; body says "N% below the Ulta price" instead of "off the listed price" for those.
- One Lancôme brand page (/brands/lancome/) instead of two; /brands/lanc-me/ is gone. Fragrance/dupe URLs unchanged.
- Core Web Vitals: first two homepage card images load eagerly with fetchpriority=high (LCP); the rest stay lazy, all decode async.

**Checks (local build on today's data):** 93 pages, all JSON-LD parses, 0 broken internal links of 1,734, no duplicate titles; sitemap.xml and llms.txt include the new pages.

**Deploy:** the box has no GitHub push login, so the patch was handed to a Cursor cloud agent to commit to main; the push triggers daily-refresh (refresh + build + IndexNow + Pages deploy). Verify next run.

**Open:** FragranceShop's store API returns 403/401 to the box (works in CI). Bing IndexNow still refuses github.io project pages (custom domain would fix). No affiliate click/sale data on the box.
