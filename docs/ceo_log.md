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

## 2026-10-18 (Sun) — daily optimization pass (Grok Bot)

**Refresh status:** site live (200). Today's scheduled daily-refresh (run 39136544946, started 10:33 AM ET, about 3h after the 7:17 AM cron because GitHub delayed it) passed build and deploy and committed afe9e6e "daily refresh" at 10:44 AM ET. Data is stamped 10:33 AM ET: 42 live deals (26 at FragranceShop, 16 at Perfumania), 12/15 dupes priced, 0/120 fetch failures, same 6 drops as yesterday. Yesterday's 5 pages (/best/fragrance-deals-under-30/, /best/luxury-fragrance-deals/, 3 /vs/ pages) all return 200 live. Yesterday's patch (a43847a) and the Impact verification tag (4cb48e5) are on main.

**Muse.ai deals:** muse_deals.json hasn't changed since Oct 15 (56 rows, last commit b4d3e5b). Nothing new to merge, and no prices were invented. Rows stay skipped for the same reasons: eBay/marketplace sellers, the Walmart PerfumesAmerica flag, sets/minis our stores don't stock, and Nordstrom Rack prices that beat our affiliate stores. The Ulta comps are already wired.

**New pages (5, data-driven via config `vs` + new config `roundups`, so they survive the rebuild)**
- /best/fresh-citrus-cologne-deals/: 11 men's/unisex citrus, aquatic and green picks from $22.95 (Acqua di Gio, Versace Pour Homme, Burberry Weekend, Bvlgari Man Wood Neroli, CK One, CK Everyone, Chrome Legend, Mefisto, Born in Roma EDT, Coach, Defy).
- /best/vanilla-sweet-fragrance-deals/: 11 vanilla/tonka/toffee/praline picks from $45.95 (La Vie Est Belle, Eilish, Donna Born in Roma, Olympea, Poême, Stronger With You Intensely, Born in Roma Intense, The Most Wanted Parfum, Le Beau, Eros, Eros Flame).
- /vs/ck-eternity-vs-eternity-air/ ($29.95 vs $20.95, both 3.4 oz EDP)
- /vs/acqua-di-gio-vs-versace-pour-homme/ ($66.95 for 3.4 oz vs $45.95 for 1.0 oz)
- /vs/stronger-with-you-intensely-vs-born-in-roma-intense/ ($70.95 for 1.7 oz vs $118.95 for 3.4 oz)
Scent-family roundups are ID lists in config with a key-notes line per bottle. Notes come from Perfumania's product descriptions; Versace Pour Homme's were cross-checked on Fragrantica because Perfumania's copy doesn't list them. Bottles that stop being live deals drop off automatically, and a roundup only renders with 3+ live picks. Each page has ItemList(Product/Offer) or 2× Product/Offer + FAQPage JSON-LD and 11–23 inbound internal links: homepage/gender chips, every member fragrance page (now links to *all* roundups that include it, not just the first), and the vs pages link to the roundups their bottles are in.

**Titles/meta**
- 88 of 93 titles were over 60 characters (Google truncates around there). A `fit()` helper now tries shorter templates until one fits, keeping the price and % hooks. Fragrance pages drop the "– Cheapest Price Oct 2026" tail ("Calvin Klein Free Cologne 3.4 oz Sale: $17.95 (74% Off)"). Brand, gender, hub and roundup pages drop "| ScentDealsDaily" when it doesn't fit. Roundups now read "… : N Picks From $X". Homepage is "Fragrance Deals Today: Up to 76% Off | ScentDealsDaily" with a lowest-price meta. Result: 96 of 98 under 60; the 2 left are long dupe names.
- 11 descriptions were over 160 characters (vs pages, roundups, hubs, 2 dupes). Shorter fallbacks plus a word-boundary `clip()` bring all 98 into the 70–160 range.
- **Canonical host bug:** CI passes SITE_URL=https://Aministan.github.io (capital A from repository_owner), so every canonical, og:url, sitemap `<loc>` and llms.txt URL was mixed-case. build.py now lowercases the host. indexnow.py lowercases URLs too, which is the likely cause of CI's Yandex 422 "Invalid key location" (the same key works from the box with the lowercase host).

**Core Web Vitals:** the 2.3 KB stylesheet is now inlined in `<head>`, which removes the only render-blocking request. Added a preconnect to cdn.shopify.com (all product images). The fragrance-page hero image gets fetchpriority=high + decoding=async. Card images stay lazy and no new assets were added.

**Checks (local build on today's data, CI env):** 98 pages, all JSON-LD parses, 0 broken internal links of 1,884, no duplicate titles or descriptions. sitemap.xml and llms.txt include all 5 new pages. Every Offer price on the new pages matches deals.json. Other $ figures on the site are derived: per-ounce prices and savings.

**Deploy:** the box has no GitHub push login, so the patch was handed to a Cursor cloud agent to commit to main. The push triggers daily-refresh (refresh + build + IndexNow + Pages deploy). Verify next run, including whether CI's Yandex ping now returns 200/202.

**Open:** Bing IndexNow still refuses github.io project pages (a custom domain would fix it). No affiliate click/sale data on the box. Impact (Ulta) is waiting on support ticket 898438. 3 dupes are still unpriced, and FragranceShop misses several dupes ("no size or concentration"). Vs and roundup pages disappear if a bottle stops being a deal (by design), which can briefly leave 404s in search results.

## Oct 18, 2026: moved to custom domain scentdealsdaily.com

**Change:** the site now builds for https://scentdealsdaily.com at the root path. build.py defaults to SITE_URL=https://scentdealsdaily.com and PATH_PREFIX="", and it writes site/CNAME (scentdealsdaily.com) on every rebuild. daily.yml passes those values explicitly. Canonicals, og:url, sitemap.xml, robots.txt, llms.txt, JSON-LD and internal links all use the new host with no /scentdealsdaily prefix. Affiliate links and the verification meta tags are unchanged. Local build: 98 sitemap URLs, the same set as before with only the host changed.

**DNS:** Cloudflare, DNS-only. A @ points to 185.199.108-111.153 and CNAME www points to aministan.github.io. GitHub Pages custom domain: scentdealsdaily.com, with Enforce HTTPS on once the cert is issued.

**Next:** resubmit https://scentdealsdaily.com/sitemap.xml in Google Search Console (new property) and Bing Webmaster. IndexNow to Bing should now work on the custom domain.

## 2026-10-19 (Mon) — daily optimization pass (Grok Bot)

**Refresh status:** site live on the custom domain. https://scentdealsdaily.com/ and every deep page checked return 200 (the 2 roundups and 3 vs pages from Oct 18, /best/fragrance-deals-under-30/, /subscribed/, sitemap.xml, llms.txt, feed.xml). The old aministan.github.io/scentdealsdaily/ address 301s to the new domain. Today's refresh came from the push-triggered daily-refresh run 39275271367 (commit c69bcfa, started 11:08 AM ET, build and deploy passed by 11:16 AM ET). The bot committed d0b8937 "daily refresh". Data is stamped 11:08 AM ET: 42 live deals (26 at FragranceShop), 12/15 dupes priced, 0/121 fetch failures, the same 6 drops. As of 11:53 AM ET today's 7:17 AM scheduled cron hadn't started yet (GitHub delays it; yesterday's started at 10:33 AM).

**IndexNow fixed by the domain move:** in CI, api.indexnow.org (Bing) answered **200** for all 98 URLs, and so did Yandex (**200**). That's the first Bing success. Both the github.io 403 and the Yandex 422 are gone.

**Muse.ai deals:** muse_deals.json is unchanged since Oct 15 (56 rows, last commit b4d3e5b). Nothing new to merge. No prices were invented and Amazon was skipped.

**New pages (5, data-driven through config `roundups` and `vs`, so they survive the rebuild)**
- /best/floral-perfume-deals/: 13 women's floral picks from $20.95 (Eternity, Eternity Air, CK Beauty, Boss Woman, Burberry London, Dylan Blue Pour Femme, Bright Crystal Absolu, Clinique Happy, Peace Love & Juicy Couture, Tom Ford Café Rose, Poême, Donna Born in Roma, La Vie Est Belle).
- /best/long-lasting-cologne-deals/: 7 men's eau de parfum and parfum picks from $45.95 (Bvlgari Man Wood Neroli, The Most Wanted Parfum, Eros Flame, Mefisto, Stronger With You Intensely, Born in Roma Intense, Azzaro Wanted EDP).
- /vs/billie-eilish-eilish-vs-eilish-no-2/ ($68.95 vs $34.95, both 3.4 oz EDP)
- /vs/la-vie-est-belle-vs-donna-born-in-roma/ ($70.95 for 1.0 oz vs $94.95 for 1.7 oz)
- /vs/eros-flame-vs-the-most-wanted-parfum/ ($45.95 vs $53.95, both 1.7 oz, EDP vs Parfum)
Key notes come from Perfumania's product descriptions (fetched today). Two bottles were left out because their listing data conflicts: Burberry Touch's copy doesn't match its usual notes, and Bottled No. 6 is typed EDP but described as EDT. Each new page has ItemList(Product/AggregateOffer) or 2× Product + FAQPage JSON-LD and 15–27 inbound internal links.

**Titles/meta**
- Display names use the canonical brand and drop a doubled sub-brand: "Hugo Boss Boss Bottled Unlimited" -> "Hugo Boss Bottled Unlimited", "Lancome Poeme" -> "Lancôme Poeme", brand-page lists "Lancome Poeme Perfume" -> "Poeme Perfume". URLs are unchanged.
- Fragrance titles drop a trailing "Spray" ("Calvin Klein Defy Spray 3.4 oz Sale" -> "Calvin Klein Defy 3.4 oz Sale").
- The 2 dupe titles over 60 characters now fit, using the name without the house prefix ("MFK Baccarat Rouge 540 Extrait Dupe: Club de Nuit Untold"). **All 103 titles are now ≤60.**
- `clip()` no longer leaves "..": it was producing "which to buy.." on long vs metas. Vs pages also get a shorter meta fallback.
- Vs "which is stronger" FAQ: correct article ("a Parfum", not "an Parfum") and real concentration ranking (EDT < EDP < Parfum), so an EDP vs Parfum pair is described correctly.
- Sponsor page: real title and meta ("Advertise on ScentDealsDaily: Featured Fragrance Deals"). The newsletter slot says "Friday deals email" instead of "daily email".

**Checks (local build on today's data, CI env):** 104 HTML pages (103 indexable + noindex /subscribed/), all 184 JSON-LD blocks parse, 0 broken internal links of 2,144, 0 github.io links, no duplicate titles or descriptions, all metas 70–160 characters, every canonical and og:url on https://scentdealsdaily.com. Every Offer price on the 5 new pages matches that bottle's deals.json price and comps, and every Offer sitewide is a deals.json price. CNAME, both Google verification tags, the Pinterest and Impact tags, the Cloudflare beacon, CJ sids (best-/cmp- on the new pages), the Brevo form, /subscribed/ and feed.xml are all intact. weekly-email.yml and send_weekly_email.py weren't touched.

**Search Console (Gmail, 4:07 AM ET today, before c69bcfa deployed):** non-critical Merchant listings warnings (validFrom, description, shippingDetails, hasMerchantReturnPolicy) and Product snippets warnings (aggregateRating, review). c69bcfa added validFrom and description. Shipping, returns and ratings stay off on purpose: we aren't the seller and have no review data. Revalidate in GSC after Google recrawls.

**Deploy:** the box still has no GitHub push login, so the patch was handed to a Cursor cloud agent to commit directly to main. The push triggers daily-refresh (refresh + build + IndexNow + Pages).

**Open:** no affiliate click or sale data is on the box. Awin approved ScentDealsDaily today (publisher 3128392); the next step is applying to fragrance advertisers. Impact (Ulta) ticket 898438 is still open. 3 dupes are still unpriced.
