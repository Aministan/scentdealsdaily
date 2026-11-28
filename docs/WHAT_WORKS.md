# What works

Future builds should read `data/winners.json` before adding pages or reordering the proven-picks row.

The file is the FragranceShop commission record for Oct 15 through Nov 27, 2026: 38 valid orders and $182.607 commission. Le Male Le Parfum (FS191154) is first, with 9 orders. Le Male Elixir (FS191152) has 4. Five orders posted on Nov 26. Only FS1609727 matched a bottle already in the file, Replica Afternoon Delight. FS1191490, FS190074, FS23395, and FS190162 are not in deals.json, so they have no bottle name and no slug. Three orders posted on the morning of Nov 27: FS254 ($66.95, commission $3.347), one grouped order FS90358|FS192138|FS90297|FS90529|FL608|FS2119 ($144.70, commission $7.232), and FS1191386 ($104.95, commission $5.247). FS1191386 is Good Girl Blush in deals.json. The other morning SKUs are not, so their slug stays null. Ten more orders posted later on Nov 27. FS89509 is not in deals.json. FS1191490 gained a second order and stays unmapped.

`slug` is the fragrance page path. `deal_id` is the row in `data/deals.json`. A SKU that is not that row's `sku` field can still point at the same fragrance when the bottle is already in the catalog. FS190011 (Abercrombie & Fitch Fierce 6.7 oz) is not in the catalog. The FragranceShop store API did not return that product, so it was not added and its slug stays null. Prices on the site still come from `deals.json`. An export price for a different size is stored on the winner row and is not printed as a checked price.

`orders` is set when the export counted that SKU alone. A pair the export did not split uses `orders_group` and `orders_group_count` on both SKUs, and `orders` stays null so the two rows are not added twice. Per-SKU commission was not in the export, so `commission` on each row is null. The period total is the top-level `commission`.

The homepage and `/best-sellers/` proven-picks row is Le Male Le Parfum, Le Male Elixir, Jazz Club, and 1 Million Lucky, sorted by order count, highest first. Le Male is 9. Elixir is 4. Jazz Club uses the shared count of 2 on FS1609839. 1 Million Lucky uses the shared count of 1 on FS89601. A row that has both its own orders and a shared group count adds them. Cards for a mapped winner get a Best seller badge. The checked price on the page is still the deals.json price.

When a new page is worth adding, start from the mapped slugs at the top of the file and use bottles that are still in `deals.json`. Skip a bottle that is not priced there.
