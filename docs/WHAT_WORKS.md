# What works

Future builds should read `data/winners.json` before adding pages or reordering the proven-picks row.

The file is the FragranceShop commission record for Oct 15 through Nov 24, 2026: 18 valid orders and $75.491 commission. Almost all of the money is in men's cologne around $80 to $95. Le Male Le Parfum (FS191154) is first, with 6 orders. Three orders arrived on Nov 23–24. FS191156 is Ultra Male Cologne 4.2 oz, the only one of those three with an exact sku in deals.json. FS90184 and FS42082 are not in deals.json, so they have no bottle name and no slug. FS42082 is not FS42081.

`slug` is the fragrance page path. `deal_id` is the row in `data/deals.json`. A SKU that is not that row's `sku` field can still point at the same fragrance when the bottle is already in the catalog. FS190011 (Abercrombie & Fitch Fierce 6.7 oz) is not in the catalog. The FragranceShop store API did not return that product, so it was not added and its slug stays null. Prices on the site still come from `deals.json`. An export price for a different size is stored on the winner row and is not printed as a checked price.

`orders` is set when the export counted that SKU alone. A pair the export did not split uses `orders_group` and `orders_group_count` on both SKUs, and `orders` stays null so the two rows are not added twice. Per-SKU commission was not in the export, so `commission` on each row is null. The period total is the top-level `commission`.

The homepage and `/best-sellers/` proven-picks row is still Le Male Le Parfum, Jazz Club, and 1 Million Lucky, sorted by order count, highest first. Le Male is 6. Jazz Club uses the shared count of 2 on FS1609839. 1 Million Lucky uses the shared count of 1 on FS89601. The Nov 24 Ultra Male order is a different bottle, so it does not change that order. Cards for a mapped winner get a Best seller badge. The checked price on the page is still the deals.json price.

When a new page is worth adding, start from the mapped slugs at the top of the file and use bottles that are still in `deals.json`. Skip a bottle that is not priced there.
