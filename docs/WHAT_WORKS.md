# What works

Future builds should read `data/winners.json` before adding pages or reordering the proven-picks row.

The file is the FragranceShop commission record for Oct 15 through Nov 28, 2026: 47 valid orders and $230.569 commission. Le Male Le Parfum (FS191154) is first by lifetime orders, with 9. Le Male Elixir (FS191152) has 7, four on Nov 27 and three on Nov 28, which is the most orders in that window. The lead Buy still uses the lifetime count, so Le Parfum stays the button. Elixir sits next to it in the homepage and /men/ folds. FS16013 is Armani Code and FS191812 is Very Good Girl, both exact SKUs in deals.json. FS254|FS9668|FS90159, FS88837, FS1191403, and FS190082 are not in deals.json, so their slug stays null. The Nov 27 orders already in the file were not counted again.

`slug` is the fragrance page path. `deal_id` is the row in `data/deals.json`. A SKU that is not that row's `sku` field can still point at the same fragrance when the bottle is already in the catalog. FS190011 (Abercrombie & Fitch Fierce 6.7 oz) is not in the catalog. The FragranceShop store API did not return that product, so it was not added and its slug stays null. Prices on the site still come from `deals.json`. An export price for a different size is stored on the winner row and is not printed as a checked price.

`orders` is set when the export counted that SKU alone. A pair the export did not split uses `orders_group` and `orders_group_count` on both SKUs, and `orders` stays null so the two rows are not added twice. Per-SKU commission was not in the export, so `commission` on each row is null. The period total is the top-level `commission`.

The homepage and `/best-sellers/` proven-picks row is Le Male Le Parfum, Le Male Elixir, Jazz Club, and 1 Million Lucky, sorted by order count, highest first. Le Male is 9. Elixir is 7. Jazz Club uses the shared count of 2 on FS1609839. 1 Million Lucky uses the shared count of 1 on FS89601. A row that has both its own orders and a shared group count adds them. Cards for a mapped winner get a Best seller badge. The checked price on the page is still the deals.json price.

Reader favorites on `/`, `/men/`, and `/best-sellers/` rank every mapped winner still in the price check. The list is the rank only. It does not print order counts, sale amounts, or times. The label is "Based on orders through ScentDealsDaily since Oct 2026." A SKU that leaves the check is left off.

When a new page is worth adding, start from the mapped slugs at the top of the file and use bottles that are still in `deals.json`. Skip a bottle that is not priced there.
