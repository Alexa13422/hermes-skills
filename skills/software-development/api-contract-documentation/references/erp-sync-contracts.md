# ERP / accounting-system sync contracts (BAS, 1C, SAP, etc.)

Depth for the recurring case: an external accounting system owns products,
prices and stock; the storefront keeps a local copy in its own SQL database.
Read alongside Step 2b (direction) in SKILL.md.

## Who owns what

The ERP is the source of truth for product identity, price, stock, barcode,
dimensions and lead time. The storefront owns everything the ERP has no concept
of and must never receive from it: carts, customer accounts and passwords,
addresses, sessions, reviews, payment data, carrier data, and the shop's own
internal primary keys. An incoming sync that touches those overwrites live state.

Merchandising values the shop computes itself (a "bestseller" tag written by a
backend job, review aggregates) are in the same category — mark them do-not-sync
explicitly, because they look like ordinary product fields.

## Two identifiers, both required

- `external_id` — the ERP's own stable object id (`bas-product-8472`,
  `bas-variant-8472-250`). Never changes when the title, price or article
  number changes. This is what the sync matches on.
- `sku` — the human-facing article number of the variant. Appears in orders,
  warehouse reconciliation, waybills, barcodes and admin search.

Matching on `sku` alone means an article-number edit in the ERP looks like a new
product and the next run creates a duplicate. Carry both, match on
`external_id`, treat `sku` as a mutable business attribute.

## Pull model (we fetch from the ERP) — required mechanics

- Opaque `cursor` + `next_cursor` pagination over a provider-guaranteed stable
  sort (`(updated_at, external_id)`), plus `limit` and `has_more`. Do not offer
  `page`/offset: rows edited mid-walk shift between pages, so the fetch skips
  and duplicates records while returning `200`.
- `snapshot_at` in every response envelope — one fixed instant for the entire
  walk, identical on all pages, so the dataset cannot drift between requests.
  Store it and pass it back as the next run's `updated_since`. Never use our own
  clock: drift between the two hosts silently drops records.
- `updated_since` as an RFC 3339 **UTC** bound with an explicitly **inclusive**
  comparison, plus local dedup by `external_id`. `>` loses every record sharing
  a timestamp with the watermark; `>=` merely repeats them, and repetition is the
  recoverable failure.
- Overlap the window on purpose (re-request a few minutes before the stored
  watermark) and make the local upsert idempotent, so a boundary record is
  re-applied harmlessly instead of lost.
- A `cursor` in the request supersedes `updated_since`, so the two can never
  disagree about where the walk starts. Expiring a cursor is `410` with a
  `cursor_expired` code, meaning "restart the walk from the stored watermark".
- `total` is optional and nullable — an exact count is often the most expensive
  part of the query, and the loop runs on `has_more` anyway.
- Deletion signal: a three-state `status` (`active` / `hidden` / `deleted`) with
  `deleted_at`, and an `include_deleted` param the consumer always sets. A record
  that merely stops appearing is indistinguishable from "unchanged", so an
  upstream deletion leaves the product on sale forever. `hidden` retains the row
  but pulls it from the storefront; `deleted` retires it. A `deleted` payload may
  carry only the id, status and timestamps.
- Split the cadence by payload weight: a light prices-and-stock endpoint polled
  every few minutes, the full catalog (descriptions, images, references) far
  less often, plus a full non-incremental pass once a day as insurance against a
  dropped increment. Polling the heavy endpoint on the fast schedule is what gets
  the integration rate-limited or banned.
- Treat a partially fetched run as not-committed for the watermark: only
  advance the stored `snapshot_at` after the last page of the run succeeds.
- What to demand of the provider so the cadence survives: an index on
  `updated_at`, the guaranteed stable ordering, and a documented rate limit with
  `Retry-After`. Without the index every poll table-scans the catalog.

## Push model (they call us) — required mechanics

- `Idempotency-Key` per batch, so a network retry does not double-apply.
- Accept asynchronously: return `202` with a `job_id`, process in a queue, and
  expose a status endpoint reporting `received/processed/failed` counts plus
  per-record errors keyed by `external_id`. A bare `200` tells the sender
  nothing about whether the rows landed.
- Authenticate with a single long random key in a custom header, stored only in
  the server's `.env`, never in code, the HTML doc, or the database, and only
  over HTTPS. Mismatch returns `401`.

## Writing into the storefront database

Go through the commerce framework's admin API or workflows, not raw SQL — direct
table writes skip price-set, inventory and search-index side effects. Minimum
columns the local schema needs for a resumable sync: the ERP's product and
variant ids, `sku`, price, quantity, and a `updated_from_<erp>_at` stamp.

Price, stock, article number and dimensions live on the VARIANT, not the
product, in any variant-based commerce model. A product with no variants cannot
be added to a cart at all.

## Storefront-visibility rules worth stating in the contract

Stock thresholds the shop applies per variant (in stock / only N left / out of
stock / backorder with lead time) belong in the doc, because they tell the ERP
side which quantity and backorder fields actually drive what the customer sees.

If price or availability filtering runs in memory over a capped page because the
value is computed per request rather than stored, say so and recommend
denormalizing a minimum price and an availability flag during sync — the person
building the sync is the only one who can supply them.
