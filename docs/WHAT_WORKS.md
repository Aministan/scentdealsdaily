# What works

Future builds should read `data/winners.json` before adding pages or reordering the proven-picks row.

The file is the FragranceShop commission export for Oct 15 to Nov 20, 2026: 15 valid orders and $62.95 commission. Almost all of the money is in men's cologne around $80 to $95. Le Male Le Parfum (FS191154) is first, with 6 orders.

A row has a `slug` only when `data/deals.json` has that exact `sku`. If it does not, `slug` is null. Do not guess a bottle for a null slug, and do not invent a price for it. Prices on the site still come from `deals.json`.

`orders` is set when the export counted that SKU alone. A pair the export did not split uses `orders_group` and `orders_group_count` on both SKUs, and `orders` stays null so the two rows are not added twice. Per-SKU commission was not in the export, so `commission` on each row is null. The period total is the top-level `commission`.

The homepage and `/best-sellers/` proven-picks row is Le Male Le Parfum, Jazz Club, and 1 Million Lucky, sorted by the order count in this file, highest first. A bottle with no mapped SKU stays at the end. Jazz Club uses the shared count on FS1609839. 1 Million Lucky has no SKU in `deals.json`, so the bundle FS89601 and FS190011 stays unmapped and does not move that bottle up the row.

When a new page is worth adding, start from the mapped slugs at the top of the file and use bottles that are still in `deals.json`. Skip a bottle that is not priced there.
