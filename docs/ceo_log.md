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

## 2026-10-20 (Tue) — daily optimization pass

**Refresh status:** site live on the custom domain. https://scentdealsdaily.com/ returns 200, and the old aministan.github.io/scentdealsdaily address 301s there. Today's push-triggered daily-refresh run 39428368704 (the Elizabeth Arden Green Tea media commit, started 13:12Z) passed build and deploy by 13:18Z. The bot committed cff2892 "daily refresh". Data is stamped 2026-10-20T13:12Z: 42 live deals (26 at FragranceShop, 16 at Perfumania), 12/15 dupes priced, 6 dropped.

**Muse.ai deals:** muse_deals.json is unchanged since Oct 15 (last commit b4d3e5b). Nothing new to merge. No prices were invented and Amazon was skipped.

**New pages (5, data-driven through config `roundups` and `vs`, so they survive the rebuild)**
- /best/woody-amber-cologne-deals/: 6 men's woody and amber picks from $17.95 (CK Free $17.95, Boss In Motion $44.95, Bvlgari Man Wood Neroli $46.95, The Most Wanted Parfum $53.95, Coach for Men $68.95, Casamorati Mefisto $189.95).
- /best/fresh-perfume-deals-under-50/: 4 women's citrus, tea and ozonic picks, all under $50 (Eternity Air $20.95, Boss Woman $25.95, Green Tea $31.95, Clinique Happy $49.95).
- /vs/dylan-blue-vs-bright-crystal-absolu/ ($64.95 for 3.4 oz vs $69.95 for 3.0 oz, both EDP)
- /vs/green-tea-vs-eternity-air/ ($31.95 vs $20.95, both 3.4 oz EDP)
- /vs/boss-unlimited-vs-boss-in-motion/ ($31.95 for 3.3 oz vs $44.95 for 3.0 oz, both EDT)
Boss Bottled Unlimited was also added to the existing fresh-citrus cologne roundup (now 12 picks from $22.95). Its published notes lead with mint and grapefruit. Key notes come from today's Perfumania product descriptions, checked against the brand or the published pyramid where the retailer copy is long. Four bottles were left out because the listing conflicts or names no notes: Azzaro Cologne's copy describes mate leaf and agarwood, not the lavender-anise-oakmoss Pour Homme pyramid; Wanted by Night's copy lists the original Wanted EDT notes (lemon, ginger, mint, apple, cardamom, tonka, amberwood), not Wanted by Night; Bottled No. 6 is still typed EDP and described as EDT; Burberry Hero's copy never names a note. Each new page has ItemList(Product/AggregateOffer) or 2× Product + FAQPage JSON-LD and 17–21 inbound internal links.

**Titles/meta**
- Gift guides now lead with the lowest checked price ("Holiday fragrance gifts: From $17.95 | ScentDealsDaily", and the same for him, her, and under $50). Metas name that bottle and the max % off. Gift sets stay empty: no boxed set is in today's deals, and the meta says so.
- Four vs titles that had lost their price to fit 60 characters now keep a price: "Eros Flame vs Most Wanted Parfum: Which to Buy? From $45.95", "La Vie Est Belle vs Donna Born in Roma Compared: From $70.95", "Stronger With You vs Roma Intense: Which to Buy? From $70.95", "Born in Roma Uomo vs Intense: Which to Buy? From $91.95". Full bottle names stay in the table and the intro.
- Priced dupe titles that had dropped the price to fit 60 characters now keep it ("Creed Millésime Impérial Dupe: Club de Nuit Milestone $27.95", "Silver Mountain Water Dupe: Club de Nuit Sillage $34.95", "Kilian Angels' Share Dupe: Khamrah Qahwa $25.95", "MFK Baccarat Rouge 540 Dupe: Amber Oud Rouge $38.95"). Unpriced dupes stay without a price. **All titles are ≤60.**
- The feed used to keep only the first 10 comparison pages, so a new vs page never made the file. It now includes every roundup and vs page, then the dupe hubs, then the 8 steepest deals (33 items today).

**Checks (local build on today's data, CI env):** 114 HTML pages (113 indexable + noindex /subscribed/), all 201 JSON-LD blocks parse, 0 broken internal links of 2,622, 0 github.io links, no duplicate titles or descriptions, all titles ≤60, all metas 70–160 characters, every canonical and og:url on https://scentdealsdaily.com. Every Offer price on the 5 new pages matches that bottle's deals.json price and comps, and every Offer sitewide is a deals.json price. sitemap.xml, llms.txt and feed.xml include the 5 new pages. CNAME, both Google verification tags, the Pinterest and Impact tags, the Cloudflare beacon, CJ sids (best-/cmp- on the new pages), the Brevo form, /subscribed/ and feed.xml are all intact. weekly-email.yml and send_weekly_email.py weren't touched. IndexNow is still the daily.yml step that runs on every push to main.

**Deploy:** committed directly to main. The push triggers daily-refresh (refresh + build + IndexNow + Pages).

**Open:** no affiliate click or sale data is in the repo. 3 dupes are still unpriced (Club de Nuit Iconic, Club de Nuit Woman, Al Nashama Caprice). No boxed gift set is in today's deals. Vs and roundup pages disappear if a bottle stops being a deal, which can briefly leave a 404 in search.

## 2026-10-21 (Wed) — daily optimization pass

**Refresh status:** site live on the custom domain. https://scentdealsdaily.com/ returns 200, and the old aministan.github.io/scentdealsdaily address 301s there. As of 11:45 AM ET, today's 7:17 AM scheduled daily-refresh run hadn't started yet (GitHub delays it; yesterday's started at 11:38 AM ET). The latest run is yesterday's push-triggered run 39450720860 (563f08d), which passed by 11:48 AM ET on Oct 20; the live data was stamped 2026-10-20T15:41Z. This pass's push triggers today's refresh. Local refresh on the box (stamped 2026-10-21T15:34Z, 11:34 AM ET): 44 live deals, 12/15 dupes priced, 0/120 fetch failures, 4 dropped (Sweet Like Candy and Ralph Lauren Romance are gone; Gucci Bloom and Lancôme Idôle are less than 15% below Ulta). Two new deals: Montblanc Legend Spirit 1.7 oz EDT $61.95 at Perfumania (30% below Ulta's $89.00) and Hermès H24 1.7 oz EDT $64.95 at Perfumania (41% off $110.00).

**Muse.ai deals:** muse_deals.json is unchanged since Oct 15 (56 rows, last commit b4d3e5b). Nothing new to merge. No prices were invented and Amazon was skipped.

**New pages (5, data-driven through config `roundups` and `vs`, so they survive the rebuild)**
- /best/cologne-deals-under-30/: 5 men's and unisex picks from $17.95 (CK Free $17.95, Azzaro Chrome Legend $22.95, Burberry Weekend $23.95, CK One $24.95, CK Everyone $29.95).
- /best/perfume-deals-under-30/: 6 women's picks from $20.95 (Peace Love & Juicy Couture $20.95, Eternity Air $20.95, Burberry London $21.95, CK Beauty $23.95, Boss Woman $25.95, Eternity $29.95).
- /vs/legend-spirit-vs-acqua-di-gio/ ($61.95 for 1.7 oz vs $66.95 for 3.4 oz, both EDT)
- /vs/ck-defy-vs-ck-free/ ($39.99 vs $17.95, both 3.4 oz EDT)
- /vs/le-beau-vs-versace-eros/ ($75.95 for 4.2 oz vs $51.95 for 1.7 oz, both EDT)
Montblanc Legend Spirit also joined the fresh-citrus cologne roundup (now 13 picks from $22.95). Key notes come from today's Perfumania product descriptions, except Legend Spirit: Perfumania's copy names no notes, so its pyramid comes from Montblanc's own product page (pink peppercorn, grapefruit, bergamot; lavender, cardamom, aquatic accord; white woods, oak moss, white musks). Bottles left out: Azzaro Pour Homme (under $30, but its copy still describes a different scent) and Burberry Touch (under $30, copy still conflicts), plus Hermès H24, which had no good pairing today. Each new page has ItemList(Product/AggregateOffer) or 2× Product + FAQPage JSON-LD and 20–23 inbound internal links.
- Configured roundups can now set `max_price`. A bottle that climbs past it drops off the page on the next rebuild, so an "under $30" or "under $50" page never lists a pricier bottle. It's set on both new under-$30 pages and on fresh-perfume-deals-under-50.

**Titles/meta**
- Brand names now follow the brand's own spelling: "Mont Blanc" -> "Montblanc" and "Hermes" -> "Hermès" in titles, metas, JSON-LD brand and the brand pages (/brands/montblanc/, /brands/hermes/). Both pages are new today. Fragrance URLs are unchanged.
- Single-deal brand pages (Bvlgari, Clinique, Coach, Elizabeth Arden, Hermès, Jean Paul Gaultier, Juicy Couture, Montblanc, Paco Rabanne, Tom Ford, Xerjoff) had thin metas like "1 verified Coach fragrance deal from $68.95 (Cologne)". They now name the bottle, size, price, store and discount ("Coach Cologne 2.0 oz for $68.95 at Perfumania, 27% off the Ulta price. Our only verified Coach deal today, checked Oct 21, 2026.").
- Multi-deal brand metas no longer show a bare "Perfume" or "Cologne" for the bottle name (Billie Eilish now reads "No.2 Perfume, Eilish Perfume").
- Display names drop a stray "Spray" before Cologne/Perfume ("Calvin Klein Defy Spray Cologne" -> "Calvin Klein Defy Cologne"). URLs are unchanged. **All titles are ≤60.**

**Checks (local build on today's data, CI env):** 123 HTML pages (122 indexable + noindex /subscribed/), all 220 JSON-LD blocks parse, 0 broken internal links of 2,958, 0 github.io links, no duplicate titles or descriptions, all titles ≤60, all metas 70–160 characters, every canonical and og:url on https://scentdealsdaily.com. Every Offer price on the 5 new pages matches that bottle's deals.json price and comps, and every Offer sitewide is a deals.json price. sitemap.xml, llms.txt and feed.xml (38 items) include the 5 new pages, and the feed and sitemap parse as XML. CNAME, both Google verification tags, the Pinterest and Impact tags, the Cloudflare beacon, CJ sids (best-/cmp- on the new pages), the Brevo form, /subscribed/ (noindex) and feed.xml are all intact. weekly-email.yml and send_weekly_email.py weren't touched. IndexNow is still the daily.yml step that runs on every push to main.

**Affiliate data (Gmail, read-only, since Oct 20):** no CJ, Rakuten or Awin approval, decline or sale email. Awin sent its welcome email at 4:16 AM ET Oct 20. Impact answered ticket 898438 at 12:43 PM ET Oct 20: the Marketplace decline stands and the requirements aren't disclosed. Their advice is to apply to brands' Impact programs directly through each brand's own "affiliate program" page. No click or sale data is in the repo.

**Open:** no affiliate click or sale data yet. All 8 CJ and 4 Rakuten applications are still pending, and so is Escentric Molecules on Awin. Impact path: apply brand by brand (Ulta and others) from each brand's partner page. 3 dupes are still unpriced (Club de Nuit Iconic, Club de Nuit Woman, Al Nashama Caprice). Hermès H24 has no notes-backed roundup or vs page yet.

## 2026-10-22 (Thu) — daily optimization pass

**Refresh status:** site live on the custom domain. The latest daily-refresh before this pass is run 39799785584 (the Oct 21 optimizer push, started 14:54Z), which passed build and deploy. The bot committed f46202e "daily refresh". Data is stamped 2026-10-22T14:54:13Z: 43 live deals (26 at FragranceShop, 17 at Perfumania), 12/15 dupes priced, 5 dropped (CK Defy has no 15% variant, so /vs/ck-defy-vs-ck-free/ does not render; Sweet Like Candy and Ralph Lauren Romance are gone; Gucci Bloom and Lancôme Idôle are under 15% below Ulta). This pass did not re-fetch prices. The push triggers today's refresh.

**Muse.ai deals:** muse_deals.json is byte-identical to the Oct 15 file (56 rows, last commit b4d3e5b). Nothing new to merge. No prices were invented and Amazon was skipped (the file has no Amazon rows). Still skipped: every eBay seller, Walmart (PerfumesAmerica), Nordstrom Rack (gift sets, or not a 15%+ discount we can sell at Perfumania or FragranceShop), and Ulta rows that are already compare prices or that belong to bottles our stores do not have at 15% off (Bloom, Idôle, Cheirosa 62, Viva La Juicy, Ari, and the Ulta gift sets and minis). No boxed set and no mini is in today's deals.

**New pages (5, data-driven through config `gift_guides`, so they survive the rebuild)**
- /gifts/cologne-gifts-for-him-under-50/: 9 men's colognes under $50, from $17.95 (CK Free $17.95, Chrome Legend $22.95, Burberry Weekend $23.95, Azzaro Cologne $25.95, Bottled Unlimited $31.95, Boss In Motion $44.95, Eros Flame $45.95, Versace Pour Homme $45.95, Bvlgari Man Wood Neroli $46.95). `max_price` 50.
- /gifts/perfume-gifts-for-her-under-40/: 9 women's perfumes under $40, from $20.95 (Peace Love & Juicy Couture $20.95, Eternity Air $20.95, Burberry London $21.95, CK Beauty $23.95, Boss Woman $25.95, Burberry Touch $27.95, Eternity $29.95, Green Tea $31.95, Eilish No. 2 $34.95). `max_price` 40. The under-$50 her guide still holds bottles from $40 up.
- /gifts/fragrance-gifts-for-teens/: 16 checked bottles under $40, men's, women's, and unisex, from $17.95. The page is a budget list. It does not call a scent a teen fragrance, because none of these listings do. `max_price` 40.
- /gifts/stocking-stuffer-fragrances/: 8 regular bottles under $25, from $17.95 (CK Free, Peace Love & Juicy Couture, Eternity Air, Burberry London, Chrome Legend, Burberry Weekend, CK Beauty, CK One $24.95). These are not minis. The minis page stays empty. `max_price` 25.
- /gifts/luxury-fragrance-gifts/: 10 single bottles whose checked compare-at is $120 or more, from $53.95 (Most Wanted Parfum $53.95/$120, Dylan Blue Pour Femme $64.95/$120, Le Beau $75.95/$130, Poême $83.95/$126, Donna Born in Roma $94.95/$145, Bottled No. 6 $95.95/$139, Burberry Hero $99.95/$137, Born in Roma Intense $118.95/$160, Mefisto $189.95/$330, Café Rose $196.95/$300).
A bottle that climbs past its cap drops off on the next rebuild. Note lines are the ones already stored from retailer descriptions. Azzaro Cologne, Burberry Touch, Burberry Hero, and Bottled No. 6 stay on a price list where they qualify, with no note line, because the retailer copy conflicts or names no notes. Each new page has ItemList (Product/AggregateOffer) and FAQPage JSON-LD, and 29–42 inbound internal links (homepage, gift nav, gender pages, roundups that share a bottle, and the bottle pages). Holiday copy runs through December 20, 2026.

**Titles/meta**
- Single-category brand titles no longer say "Perfume & Cologne" when the page is only one of those. Cologne: Azzaro, Bvlgari, Giorgio Armani, Jean Paul Gaultier, Coach, Xerjoff, Montblanc. Perfume: Juicy Couture, Tom Ford, Billie Eilish, Elizabeth Arden, Lancôme, Paco Rabanne, Clinique. Hermès, which is unisex only, is "Hermès Fragrance Deals: Up to 41% Off Today". Mixed brands stay "Perfume & Cologne".
- "Billie Eilish Eilish vs Eilish No. 2 Compared" is now "Eilish vs Eilish No. 2: Which to Buy? From $34.95". The full names stay in the table and the intro.
- Fragrance metas now carry the discount and the dollar savings ("Coach Cologne 2.0 oz is $68.95 at Perfumania, 27% below the $94.00 Ulta price (save $25.05). Sealed bottle, checked Oct 22, 2026.").
- Dupe-hub metas name the dupes ("3 Creed dupes: Club de Nuit Intense Man, Club de Nuit Sillage, Club de Nuit Milestone. Prices from $27.95.").
- The three unpriced dupe metas now say no live retailer price is verified yet. **All titles are ≤60. All metas are 70–160.**

**Checks (local build on today's data, CI env):** 130 HTML pages (129 indexable + noindex /subscribed/), all 231 JSON-LD blocks parse, 0 broken internal links of 3,350, 0 github.io links, no duplicate titles or descriptions, all titles ≤60, all metas 70–160 characters, every canonical and og:url on https://scentdealsdaily.com. Every Offer price on the 5 new pages matches that bottle's deals.json price and comps, and all 914 Offer prices sitewide are a deals.json price or comp. sitemap.xml (129 URLs), llms.txt and feed.xml (48 items) include the 5 new pages. CNAME, both Google verification tags, the Pinterest and Impact tags, the Cloudflare beacon, CJ sids (gifts- on the new pages), the Brevo form, /subscribed/ (noindex) and feed.xml are all intact. weekly-email.yml and send_weekly_email.py weren't touched. No script fetched a CJ or other affiliate tracking URL; the build only string-checks those links. IndexNow is still the daily.yml step that runs on every push to main.

**Deploy:** committed directly to main. The push triggers daily-refresh (refresh + build + IndexNow + Pages).

**Open:** no affiliate click or sale data is in the repo. 3 dupes are still unpriced (Club de Nuit Iconic, Club de Nuit Woman, Al Nashama Caprice). No boxed gift set and no mini or travel size is in today's deals. CK Defy is not a live deal, so its vs page stays off. Hermès H24 still has no notes-backed roundup. Vs and gift-guide pages drop a bottle that stops being a deal, which can briefly leave a thin page; the URL stays so it does not 404. Owner-only: resubmit sitemap if Search Console has not picked up the new gift URLs, and the affiliate applications (CJ, Rakuten, Awin, and brand-by-brand Impact) still have to be finished in those dashboards.

## 2026-10-23 (Fri) — daily optimization pass

**Refresh status:** site live on the custom domain. https://scentdealsdaily.com/ returns 200 (42 deals, checked Oct 23), and the old aministan.github.io/scentdealsdaily address 301s there. Today's push-triggered daily-refresh is run 39958311389 (the Billie Eilish media commit, started 13:05Z), which passed build and deploy. The bot committed 0624e31 "daily refresh" at 13:14Z. Data is stamped 2026-10-23T13:05:16Z: 42 live deals (26 at FragranceShop, 16 at Perfumania), 12/15 dupes priced, 6 dropped (CK Defy still has no 15% variant, so /vs/ck-defy-vs-ck-free/ stays off; Hermès H24 is no longer a live deal; Sweet Like Candy and Ralph Lauren Romance are gone; Gucci Bloom and Lancôme Idôle are under 15% below Ulta). This pass did not re-fetch prices. The push triggers another refresh.

**Muse.ai deals:** muse_deals.json is byte-identical to the Oct 15 file and to the file attached for this run (56 rows, sha256 9fbb4705b29545a5…). Nothing new to merge. The file has no FragranceShop or Perfumania rows, and no Amazon rows. Still skipped: every eBay seller, Walmart (PerfumesAmerica), Nordstrom Rack, and the Sephora reference row. Ulta rows stay compare prices already on the bottles we sell. No prices were invented.

**New pages (5, data-driven through config `gift_guides`, `roundups`, and `vs`, so they survive the rebuild)**
- /gifts/secret-santa-fragrances-under-30/: 13 regular bottles under $30, men's, women's, and unisex, from $17.95. The $25 stocking page is the tighter cap. This one adds Boss Woman $25.95, Azzaro Cologne $25.95, Burberry Touch $27.95, CK Everyone $29.95, and Eternity $29.95. It does not call a scent a Secret Santa fragrance. `max_price` 30. Minis stay off.
- /gifts/christmas-perfume-gifts-for-mom/: 8 women's perfumes at $50 and up, from $59.95 (Olympea $59.95, Dylan Blue Pour Femme $64.95, Eilish $68.95, Bright Crystal Absolu $69.95, La Vie Est Belle $70.95, Poême $83.95, Donna Born in Roma $94.95, Café Rose $196.95). For a mom or a wife. No overlap with the under-$50 her guide. `min_price` 50, new on gift guides so a bottle that falls under the floor drops off on the next rebuild. The page does not call a scent a mom perfume.
- /gifts/cologne-gifts-for-dad/: 13 men's colognes at $50 and up, from $51.95 (Eros $51.95 through Mefisto $189.95). For a dad or a husband. No overlap with cologne gifts for him under $50. `min_price` 50. The page does not call a scent a dad cologne.
- /best/warm-spicy-cologne-deals/: 4 men's picks whose stored retailer notes name cinnamon, cardamom, black pepper, or ginger, from $44.95 (Boss In Motion $44.95, Eros Flame $45.95, The Most Wanted Parfum $53.95, Stronger With You Intensely $70.95). Vanilla-only bottles stay on the vanilla roundup. A fresh citrus that only mentions pink pepper stays on the fresh page.
- /vs/most-wanted-vs-stronger-with-you/: The Most Wanted Parfum $53.95 vs Stronger With You Intensely $70.95, both 1.7 oz (Parfum vs eau de parfum). Notes are the ones already stored from retailer copy (ginger, woods, bourbon vanilla; pink pepper, toffee, cinnamon, vanilla).
Azzaro Cologne and Burberry Touch stay on the Secret Santa price list with no note line, because the retailer copy conflicts. Wanted by Night, Burberry Hero, and Bottled No. 6 can sit on the dad list the same way. Wanted by Night also left the long-lasting roundup (now 6 picks from $45.95): its stored note line was the original Wanted pyramid, not this bottle. Hermès H24 is not a live deal today, so it still has no notes-backed page. Holiday copy runs through December 20, 2026. Each new page has ItemList (Product/AggregateOffer) or 2× Product/Offer and FAQPage JSON-LD, and 20–42 inbound internal links (homepage, gift nav, gender pages, related roundups, and the bottle pages).

**Titles/meta**
- Homepage guide chips were rendering as the literal text `{bestchips()}`. They now render the budget, scent, dupe, and vs links.
- Minis title "Stocking stuffer fragrance minis & travel sizes: From $14.95" (60 characters) is now "Fragrance minis and travel sizes: From $14.95". The meta names Fantasy at $14.95 and the max discount (up to 65% off).
- "Fragrance gift sets: From $76.95 | ScentDealsDaily" is now "Designer fragrance gift sets: From $76.95 | ScentDealsDaily", and the meta includes up to 29% off.
- "Fragrance gift sets for the holidays: From $31.95" is now "Holiday fragrance gift sets: From $31.95 | ScentDealsDaily", and the meta includes up to 53% off.
- Gift-guide metas include the biggest discount on the page when that still fits 160 characters.
- Unisex meta now names the two bottles: "CK One $24.95, CK Everyone Unisex Fragrance $29.95" (H24 is gone, so Hermès is not on this page).
- Multi-deal brand metas name the price span and the max discount ("4 verified Hugo Boss perfume & cologne deals from $25.95 to $95.95 … up to 57% off").
- The brands index meta is a full sentence again (it had been clipped to "checked.").
- The Kilian dupe-hub meta now carries the scent notes (Khamrah boozy cinnamon-vanilla, Khamrah Qahwa coffee). **All titles are ≤60. All metas are 70–160.**

**Checks (local build on today's data, CI env):** 133 HTML pages (132 indexable + noindex /subscribed/), all 243 JSON-LD blocks parse, 0 broken internal links of 4,193, 0 github.io links, no duplicate titles or descriptions, all titles ≤60, all metas 70–160 characters, every canonical and og:url on https://scentdealsdaily.com. Every Offer price on the 5 new pages matches that bottle's deals.json price and comps, and all 1,030 Offer prices sitewide are a deals.json price or comp. sitemap.xml (132 URLs), llms.txt and feed.xml (56 items) include the 5 new pages, and the feed and sitemap parse as XML. CNAME, both Google verification tags, the Pinterest and Impact tags, the Cloudflare beacon, CJ sids (gifts-, best-, and cmp- on the new pages), the Brevo form, /subscribed/ (noindex) and feed.xml are all intact. weekly-email.yml and send_weekly_email.py weren't touched. No script fetched a CJ or other affiliate tracking URL; the build only string-checks those links. IndexNow is still the daily.yml step that runs on every push to main.

**Deploy:** committed directly to main. The push triggers daily-refresh (refresh + build + IndexNow + Pages).

**Open:** no affiliate click or sale data is in the repo. 3 dupes are still unpriced (Club de Nuit Iconic, Club de Nuit Woman, Al Nashama Caprice). CK Defy is not a live deal, so its vs page stays off. Hermès H24 dropped on today's refresh, so it still has no notes-backed page; /brands/hermes/ and /fragrance/hermes-h24-eau-de-toilette/ leave the sitemap with this build. A unisex gift page was skipped: only CK One and CK Everyone are unisex deals today, and both are already on Secret Santa and on CK One vs CK Everyone. Vs and gift-guide pages drop a bottle that stops being a deal. A roundup URL can 404 if it falls under 3 live picks. Owner-only: resubmit the sitemap if Search Console has not picked up the new URLs, and the affiliate applications (CJ, Rakuten, Awin, and brand-by-brand Impact) still have to be finished in those dashboards.
