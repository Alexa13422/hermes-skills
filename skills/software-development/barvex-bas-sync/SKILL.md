---
name: barvex-bas-sync
description: "Use when syncing Barvex catalog from BAS/1C."
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Medusa, BAS, 1C, Catalog-Sync, Barvex, Pull-Integration]
    related_skills: [api-contract-documentation, agent-delegation-routing]
---

# Barvex ← BAS/1C catalog sync

## When to Use

Use when touching the Barvex ↔ BAS/1C integration: the sync worker, the pull
contract, stock or price updates, tombstones, or the `bas-sync` module. BAS is
a critical path in this repo — changes there warrant a verifier-critic pass,
not just a visual check.

Barvex is a Medusa v2 backend (`apps/backend`) + Next.js storefront
(`apps/storefront`) at `/home/alexa/programming/Barvex/barvex`.
BAS/1C is the master source for products, prices and stock.

## Direction is pull, not push

Barvex calls BAS on a schedule with GETs; BAS pushes nothing. The endpoints
are implemented by the BAS side, so our job is the sync worker, not an API.
Contract (source of truth, redocly-valid): `docs/api/bas-openapi.yaml`;
human-readable page for the integrator: `docs/api/bas-index.html`.

Base path carries the version: `https://<host>/api/barvex/v1`. `BAS_API_URL`
must include that prefix — the client concatenates `apiUrl + path`, so a bare
host returns 404 on every call.

## Deletion and out-of-stock are different signals

Conflating them is the central trap. `status: deleted` means the item is gone
from the BAS nomenclature forever; `inventory_quantity: 0` means it exists and
is temporarily sold out. Keep them as two independent code paths.

The owner's standing decision: a withdrawn product is made UNBUYABLE, not
unpublished. Every retirement signal resolves to stock 0 + `allow_backorder:
false` + `manage_inventory: true`, leaving the page live. Unpublishing kills
the SEO page and the back-in-stock path, so it is never the answer to a stock
or tombstone signal. The ONLY case that touches product status is corrupt
data.

| BAS signal | Action |
|---|---|
| `deleted` | stay published, make unbuyable; mark `metadata.bas_deleted_at` |
| `hidden` | stay published, make unbuyable |
| `active` + qty 0 | do not touch publication at all, write stock only |
| absent from a full snapshot | make unbuyable (daily full pass) |
| variant gone from a product | retire that variant; last one gone → whole product unbuyable |
| `price.amount_minor: 0` | `status: "draft"` + raise an error; do NOT overwrite the old price |

Never physically delete a product, with or without orders: Medusa order lines
reference the variant, so deletion either breaks order history or leaves a
dangling reference, making returns unresolvable.

Process a minimal `deleted` product record before ordinary content mapping: the
contract permits tombstones without title or variants, so a mapper requiring
those fields would reject retirement and leave a sellable item behind. For an
existing product, retain the page and variant IDs while disabling backorder and
setting stock to zero; for an unknown external ID, log and skip. Write a failing
regression test for this path before changing the workflow, then verify it on a
copied DB. Model availability and snapshot differences as pure functions
(`policy.ts`: `resolveAvailability`, `diffVariants`, `diffSnapshot`) so decisions
are unit-testable. Missing `lead_time_days` falls back to a named constant
(currently 14 days); missing `allow_backorder` logs a warning rather than
silently defaulting.

## Deletion can arrive as silence

A record hard-deleted in BAS may simply stop appearing in `updated_since`
results with no `deleted` status — indistinguishable from "unchanged", so it
lives on the storefront forever. Run one full pass per day without
`updated_since` and retire anything carrying a `bas_external_id` that the
snapshot does not contain. This is what `snapshot_at` is for.

## Stock writes can oversell

The stock pass runs every 5–15 min and writes an absolute value, so a unit
sold since the last BAS read gets added back. Either reconcile against Medusa
reservations or accept the drift and enforce an availability check at
checkout, not just on the product card.

`allow_backorder` + `lead_time_days` must come from BAS explicitly on every
variant. The storefront distinguishes «Немає» from «Під замовлення» only by
that flag (`apps/storefront/src/lib/util/product-fields.ts`,
`LOW_STOCK_THRESHOLD = 5`); without it every zero reads as "gone".

## Keys, money, pagination

Use distinct immutable `product.external_id` (card) and `variant.external_id`
(shade/size) as upsert keys; SKU is an editable article, never a matching key.
Create BAS-owned cards at first import. Leave existing manual cards without BAS
IDs untouched rather than matching by name or SKU; temporary duplicates are
acceptable. Money is `{amount_minor, currency_code}` in kopecks — convert via
integer parts, never float arithmetic.

Tags and handles are NOT in the BAS contract — see "Field ownership" below. Any
tag-resolution machinery is for our own jobs (`tag-bestsellers`), not for sync
input.

Pagination is cursor-based (`cursor`/`next_cursor` over a stable
`(updated_at, external_id)` order), never `page`, which shifts the window
between requests and silently duplicates or skips rows. Advance the watermark
only after a complete successful pass: if even one Medusa write fails, mark
the run failed, clear the page cursor so the rejected item is retried, and do
not retire products missing from the incomplete snapshot. Guard this in both
the orchestrator and `finishRun`; a state service that accepts `failed > 0`
can otherwise record a false success. Guard the paginator against a repeated
`next_cursor` and cap `Retry-After`, or a buggy server loops forever or parks
a job for hours.

A saved checkpoint is only real if the paginator ACCEPTS a starting cursor.
Verify the generator's signature takes one and that the first HTTP request
carries it; a paginator that derives its cursor internally turns every
`saveCheckpoint` into a write nobody reads, and a failure deep in the catalog
silently re-reads it from page one. Seed the seen-cursor set with the restored
value so a resume cannot loop on it. The daily full pass is the deliberate
exception — it must start from zero to get a whole snapshot for `diffSnapshot`.

On a 410 cursor-expired, clear the stored cursor at the point of failure. The
cursor is dead permanently, so leaving it in state makes the next scheduled
run restore it and fail identically forever until someone clears it by hand.

## Optional card content and ownership

Admin-authored text is NOT fed from BAS: `description`, `subtitle`,
`ingredients`, `how_to_use` are all owned by the Medusa admin. Only
`description` gates publication; the other three are optional and never block
promoting a draft. Remove them from the product zod schema, the mapper (so
`metadata` carries ONLY `bas_external_id`) and `docs/api/bas-openapi.yaml` — a
"map it when nonblank, preserve when absent" merge is NOT protection, because
BAS keeps sending the field and wins the `{...existing, ...mapped}` merge every
pass. Verified live: admin writes all four, sync runs, all four byte-identical
afterwards.

When flipping a field to admin-owned, the OLD test that asserted the mapping
("передає заповнений BAS-контент у поля картки") encodes the behaviour the
owner just revoked — rewrite it to assert the field is ignored, do not delete it
silently. `tsc` finds these because the field vanished from `BasProduct`/
`ProductInput`.

The defensive merge still matters for fields BAS may send anyway and for a
future contract change: never mistake a missing field for an instruction to
erase content. Keep metadata keys outside BAS's ownership, especially
`seo_ready`, when updating. If brand or categories are absent, preserve admin
associations; if BAS supplies IDs, resolve them to real Medusa entities/links
before writing. A mapper exposing external IDs is not proof that the
orchestrator linked them. Check the storefront's whole-section behavior when an
optional field is absent, then verify a second sync preserves manual content on
a real copied DB.

Manage product photos through the standard Medusa Admin, one card at a time for
initial launch; production uploads use an S3-compatible file provider. Defer
bulk import until needed. The BAS contract may still contain image URL fields,
but do not rely on or overwrite admin-uploaded product/variant photos with them.
Test upload → repeated sync → unchanged gallery and thumbnail on the copied DB.
For the custom Brand model, check both assignment paths: Medusa's standard product
media upload does not imply its standard Admin can assign a custom module link.
Verify a real product↔brand link via the admin route or explicitly implement one;
never equate a brand CRUD page with a product-brand assignment UI.

## Cross-layer acceptance gates

Before calling the connector ready, trace every contracted field through BAS
payload → runtime schema → mapper → Medusa workflow → DB row/link → storefront.
Check both initial create and subsequent update: a mapped price can be silently
lost when the variant update omits `prices`. Follow `references/medusa-pricing.md`
for the verified price-set workflow (the BAS-owned sale-list path is retained in
code but no longer fed from BAS — see "Field ownership"). Inspect actual DB rows
after first, repeated and changed-price passes, then compare what a guest sees.
Unit tests of a pure price plan do not prove Medusa's graph relations or
workflow semantics. Check the full variant round trip (present → absent → present)
with the same Medusa variant ID and inventory link. For BAS reference IDs, do
not assume a mapper carrying external IDs created actual brand/category links;
resolve them safely and test absent fields preserve manual associations. Test
product and variant metadata preservation separately because a merge at the
product level does not protect manually enriched variant metadata. Before
accepting absolute stock writes, determine whether BAS quantity includes or
excludes reservations originating in Medusa, then test an active reservation;
otherwise availability may be double-subtracted or replenished incorrectly.

## Required vs optional fields

The owner's rule: a product cannot exist without its required fields; everything else is optional, and an
absent optional field hides its WHOLE storefront section rather than rendering an empty one. Enforce
required fields in the zod schema or mapper so a bad record fails loudly at ingest instead of creating a
half-empty card.

Enforced at ingest: `external_id`, `status`, `updated_at` on every entity; `title` (mapper-level); variant
`sku`, `price`, `inventory_quantity`; variant dimensions when `shippable: true`. `description` is required
for PUBLICATION but not for ingest — it is admin-authored, so the publish policy gates on it instead.

When the owner must decide which fields are mandatory, enumerate the ACTUAL schema fields grouped by
entity with the current enforced/optional state marked, rather than proposing a list from memory. Read
`modules/bas-sync/types.ts` for the live set; the contract in `docs/api/` can lag behind it. `subtitle` is
a 1–2 sentence short description used next to the price and as the SEO description with a fallback to
`description`; it is admin-authored.

## Field ownership: BAS vs admin

The owner's boundary, and the reason most "missing field" bugs are actually
ownership bugs. BAS owns IDENTITY, the REGULAR price, STOCK and dimensions:
`external_id`, `status`, `updated_at`, `title`, `price`, `inventory_quantity`,
`shippable` + dimensions. Everything a human curates belongs to the Medusa
admin: `description`, `subtitle`, `ingredients`, `how_to_use`, slug/`handle`,
tags, photos, discounts, brand, categories. After this cleanup the BAS Product
schema is exactly `external_id`, `status`, `updated_at`, `title`, `images`,
`brand_external_id`, `category_external_ids`, `variants`, `deleted_at`.

Consequences to enforce in the schema, not just in the mapper:

- Slug is generated on our side. Keep `handle` out of the product schema
  entirely; a BAS-supplied slug would overwrite a curated URL and break SEO.
  Brand and category `handle` are unaffected — those are separate entities.
  "We own the slug" still requires us to BUILD one (`modules/bas-sync/handle.ts`,
  `buildBasProductHandle(title, externalId)`) and set it on CREATE only. Leaving
  `handle` unset is not neutral: Medusa derives it from `title` via `toHandle`,
  and `product.handle` carries a unique partial index, so a second BAS product
  with the same name fails to import forever. Append the BAS id as a suffix,
  and do it in the zero-price quarantine create branch too. `toHandle` keeps
  Cyrillic (`\p{L}`), so slugs are readable, not empty.
- Tags are assigned in the admin AFTER sync. Drop `tags` from the contract;
  mapping them makes every pass fight the admin for the same field.
- BAS sends ONE price. Remove `original_price` from variant and inventory
  schemas: the struck-through price is an admin-made price list, so a sync that
  writes it also deletes it on the next pass when BAS omits it. Then DELETE the
  sale machinery rather than calling it with `originalPrice: null` — a dead
  branch still ran `listPriceLists({}, {take: 1000, relations: ["prices"]})` per
  variant and could create a duplicate BAS price list that permanently throws
  "кілька price lists". `buildBasPriceSyncPlan` should filter out every price
  carrying a `price_list` and return `{base}` only, so manual discounts are
  invisible to sync by construction.
- `description` is required FOR PUBLICATION but authored in the admin, so a
  record without one must not fail ingest — it lands as `draft`. Removing it
  from the schema is NOT enough: delete the mapper's `description` mapping too.
  A "preserve when absent" merge still overwrites the curated text whenever BAS
  sends anything, which a mock faithfully reproducing the old contract will do.
  Verified live: admin writes a description, sync runs, text must be byte-identical
  afterwards. Slug, tags and `published` status survived that same pass while the
  description did not — so test each owned field separately, never as a group.
- Removing a field can orphan its zod helper (e.g. `tagSchema`) and a whole
  module (`modules/bas-sync/tags.ts` + its spec). Grep for the symbol outside
  tests and delete the dead module, or the suite keeps testing a code path that
  no longer runs.

When removing a field from the contract, delete it in all five places or `tsc`
and the suite will disagree: zod schema (plus any `superRefine` comparing it),
mapper types and output, the workflow create/update branches, the fixture mock,
and `docs/api/bas-openapi.yaml` (field refs AND the now-orphaned component
schema). Deleting a `superRefine` body can leave an empty `.superRefine(() => {})`
that silently passes — remove the call, not just its contents.

## Publication status is a policy decision, not a BAS field

Never map BAS `status` straight onto Medusa `status`. Route it through
`modules/bas-sync/publish-policy.ts` (`resolveBasProductStatus`), which returns
`{status, reason}`:

| Case | Result |
|---|---|
| new product | `draft` / `new_product_awaits_admin_content` — even if BAS sent a description |
| existing, no description | `draft` / `description_required_for_publish` (whitespace is not a description) |
| BAS `hidden` | `draft` / `bas_hidden` |
| was unpublished BY SYNC, cause gone, description present | `published` / `restored_after_bas_recovery` |
| otherwise | keep current status / `admin_owned_status` |

New cards are always `draft` because a human still has to write the description
and decide. Sync must never raise an existing product to `published` on its own
— EXCEPT to undo its own demotion.

Unpublishing must be REVERSIBLE or a brief BAS glitch strands a product in
draft forever: the rule "existing draft stays draft" cannot tell an admin's
deliberate draft from the sync's own demotion. Write `metadata.bas_unpublished_by_sync`
(`BAS_UNPUBLISHED_MARKER`) whenever sync demotes a PUBLISHED product — in the
hidden branch, the missing-description branch, AND the zero-price quarantine,
which is a separate code path that bypasses the policy entirely. Clear it by
assigning `null`, never `delete obj[key]`: Medusa MERGES metadata, so a deleted
key keeps its old value in the DB and the marker sticks forever. Verified live:
`published → draft+marker=true → published, marker=-` while an admin-authored
draft on another product stayed untouched.

The policy needs the CURRENT description to judge an existing product, so add
`description` to the `query.graph` `fields` of the existing-product lookup and
to the `ExistingProduct` type. Reading it from the BAS payload only tells you
what BAS sent, which for this field is nothing — the policy would then demote
every curated card to draft on every pass.

## Where to run a verification stack

Before a final review, strip CRLF-only churn: loop the modified files and
`git checkout --` every one whose `git diff --ignore-cr-at-eol` is empty (59 of
73 files here). A reviewer handed that noise reports phantom findings and misses
real ones.

Run the critic on the DIFF with the ownership rules restated in the prompt, and
ask for CRITICAL/MAJOR only — an unbounded severity request buries real data-loss
bugs under style notes, and its line numbers refer to the diff, not the files.
Verify each claim against the code before acting: it flagged "nobody generates
handle" (true, real bug) and "BAS overwrites admin content" for `subtitle`/
`ingredients`/`how_to_use` (an ownership question the owner never decided — ask,
do not silently change).

Full mechanics — host choice, mock phases, DB cloning, WSL↔Docker networking,
acceptance sequence: `references/verification-stack.md`.

Count the PRISTINE source DB as `count(*) filter (where deleted_at is null)`
alongside the raw total and the `bas_external_id` count. A bare `count(*)` and a
not-deleted count differ legitimately (112 rows vs 38 alive here) and the
mismatch between two passes looks exactly like you corrupted the source; only
`bas_products = 0` actually proves it is untouched.

Make every acceptance helper script idempotent. A fixture script using
`upsertProductTags`/create on a pre-existing tag dies with `invalid_data: ...
already exists` on the second run, which reads as a product bug until you open
the log. List-then-create-missing instead.

Always-on essentials: never run Postgres, a backend or a storefront on the dev
Pi (the owner has said so — almost no free RAM); the stack goes on the Windows
PC over Tailscale, and `tailscale status` tells you it is asleep before SSH
times out. The mock's `BAS_MOCK_PHASE_FILE` phases are NUMERIC (1/2) and cannot
express a per-product `status: "hidden"` — patch the mock source for that product
with a `.bak` restore instead of inventing a phase name. Write only to a FRESH clone of the pristine Medusa DB, created by the
parameterised script with its `.env` name guard. Use the smallest BAS stand-in
that serves the pull contract, never a second full BAS app. Confirm the mock's
actual running phase before every pass, and strip contract-removed fields from
the mock too. A green unit suite, a clean process exit and a `/health` response
prove nothing about catalog state — inspect rows, links, stock and state after
each pass, and never call the sync complete before a real DB pass plus the
relevant UI behavior. Keep credentials out of every artifact and report.

## Brand and category references

Brands are MANUAL by the owner's decision: BAS will not supply brands, admins create and assign them in the Admin UI, and `brand.bas_external_id` stays empty. `/reference/brands` exists in the BAS client but is deliberately never called — there is no brand auto-creation. Verified by stripping `brand_external_id` from the mock and syncing three times: manually linked brands (`bas_external_id=NULL`) and previously BAS-linked ones both survive, active link count unchanged. Keep the ID-based resolver anyway — it is what makes an absent field a no-op instead of an erasure.

Brand identity lives in `brand.bas_external_id` (migration `Migration20261101000000`, unique partial index where `deleted_at is null`). When adding a column via hand-written migration, also patch `migrations/.snapshot-brand.json` (column entry + index `expression`), or the next `medusa db:generate` emits a duplicate migration.

`product-brand` link is NOT a list on the brand side: `createLinksWorkflow` throws `Cannot create multiple links` when the product already has a different brand. Changing a brand must be `dismissLinksWorkflow` on the old link, then create — see `workflows/link-bas-brand.ts`.

Resolve references BEFORE any product mutation (`planBasReferences`, then `writeBasReferences`). Resolving after `createProductsWorkflow`/`updateProductsWorkflow` leaves half-written products when a reference is NOT_FOUND.

`category_ids` in `updateProductsWorkflow` REPLACES the whole category set. Merge manual categories (those without `metadata.bas_external_id`) back in, or BAS silently unassigns admin-added ones. `metadata.bas_external_id` on categories has no unique constraint, so reject `length > 1` instead of taking `[0]`.

Absent, `null`, and `[]` all mean "BAS does not manage this": never clear manual links. Keep the zod schema `.nullable().optional()` for `category_external_ids`, otherwise an explicit `null` from BAS fails validation and skips the product entirely.

A new BAS identity column needs a fill path: `getBrandInput` in `api/admin/brands/brand-input.ts` is shared by both admin routes, and the field must be editable in `admin/routes/brands/page.tsx`. The shared validator must take a `partial` flag for the UPDATE route: coercing an absent field to `null` means any client that does not send `bas_external_id` silently wipes the key, and every product referencing that brand then fails NOT_FOUND. Omit the field from the result when it is `undefined` and `partial`; only an explicit empty string clears it.

Brand module files are CRLF. Editing them with tools that normalize line endings rewrites the whole file and buries the real change. Verify with `git diff --ignore-cr-at-eol --stat` and `git checkout --` any file whose only change is line endings.

### Acceptance run for references

Full sequence, SQL shapes and remote-execution mechanics: `references/reference-acceptance-runs.md`.

Always-on essentials: the link table is `product_product_brand_brand` (module prefix doubled), categories live in `product_category_product`; clone test DBs from the pristine source with a parameterised script plus an `.env` name guard; seed `brand.bas_external_id` and category `metadata.bas_external_id` BEFORE the first sync, or every product with a reference fails NOT_FOUND; never read bare link counts, group them by BAS key; put every remote SQL/grep/exit-code check in a `.sh` file rather than inline over SSH.

## Project conventions that bite

- Comments and docstrings in this repo are Ukrainian, explaining WHY;
  `src/jobs/tag-bestsellers.ts` and `src/modules/nova-poshta/client.ts` are
  the tone reference.
- Throw `MedusaError`, not plain `Error`: Medusa's HTTP layer masks plain
  errors as "An unknown error occurred" and the real cause is lost.
- Unit tests must be named `*.unit.spec.ts` or jest will not find them.
  Run them from the repo root: `npm run test:unit --workspace=apps/backend`.
  After a focused RED→GREEN cycle, run the full suite and TypeScript check;
  report inherited admin type errors separately from new BAS errors. A green
  unit suite is not evidence of a successful Medusa workflow or storefront.
- The volume option must be titled exactly `Об'єм` or the storefront misses it.
  Give a variant without volume or shade a neutral product option and matching
  variant value: Medusa's create-products workflow requires product options even
  for a single plain variant. Verify this with a real create on a copied DB;
  mapper tests alone cannot validate the workflow contract.
- A custom Medusa module resolves dependencies from its own module container;
  declare `Modules.LOCKING` in that module's dependencies before using it in
  the sync state service. Global registration alone does not make it resolvable
  there. For one-off Medusa execution, use an `exec` script receiving
  `{ container }` and invoke the orchestrator; a scheduled-job export is not
  necessarily an `exec` entrypoint.
- Filters work on native product tags only — Medusa cannot filter metadata.
- A new custom module needs a generated migration (see `modules/brand/`
  for the shape); without it the first query fails on a missing table.
  `npx medusa db:generate <module>` needs a reachable Postgres and otherwise
  hangs with no output before an `ECONNREFUSED` — when none is available,
  hand-author the file under `src/modules/<mod>/migrations/` and mirror one
  Medusa generated itself (`grep -rn 'check (' src/modules/*/migrations/*.ts`).
  The DDL must match the model exactly, since a mismatch surfaces only at
  runtime as the first sync failure: `model.enum([...])` becomes
  `"status" text check ("status" in ('a','b')) not null default 'a'`;
  `.unique()` becomes a PARTIAL unique index `WHERE deleted_at IS NULL` and
  never a table constraint, or one soft-deleted row permanently blocks
  recreating that key; and `created_at`/`updated_at`/`deleted_at` plus the
  partial `deleted_at` index must be added by hand because `model.define`
  implies them and they never appear in the model body.
- A fixture or mock server is only trustworthy once its payloads pass the
  project's OWN schemas. Import the real zod schemas and `safeParse` every
  record (`npx tsx` runs a throwaway script against `.ts` sources directly)
  instead of trusting your reading of the contract — `superRefine` rules like
  "`deleted_at` required when status is deleted" reject hand-written fixtures
  that look fine.
- Build the BAS stand-in with zero dependencies (`node:http` only) so it runs
  anywhere without an install, give each fixture product a comment naming the
  availability rule it exercises, and drive the hard cases by env var: a second
  "phase" that drops a product and a variant WITHOUT a `deleted` status is the
  only way to exercise silent deletion, plus switches for an injected 503 +
  `Retry-After` and a 410 on the second cursor.
- Kill background node by pattern (`pkill -f 'node scripts/<name>'`), not by the
  PID the terminal tool returns — that PID is the shell wrapper, so the real
  listener survives, the relaunch dies on `EADDRINUSE`, and the stale instance
  keeps answering with old data. Confirm via a version/phase field in the
  health response rather than assuming the restart took.
- A module registered in `medusa-config.ts` is NOT wired up. Grep for a
  reference to it outside its own directory and tests before calling the
  feature done — a module with no job, workflow or route that constructs its
  client never runs, and its unit tests stay green the whole time.
- Concurrency guards belong in `Modules.LOCKING`, not in read-then-write on a
  state row. Two scheduled workers can both read `idle` and both claim the
  run, then rewrite the catalog simultaneously. The locking module is already
  registered in `medusa-config.ts` behind `REDIS_URL`.
- A lock test that mutates one shared mock object proves nothing: the reads
  serialize, so the race cannot occur. Hold the first read open on a deferred
  promise and start the second claim before it resolves.
- Write to Medusa through core workflows, but keep product, variant and stock
  updates separate in BOTH the catalog and frequent inventory paths. Do NOT
  pass a partial `variants` array to product update/deep-update: omitted variants
  can be physically deleted, breaking order history and leaving inventory
  items behind. Use the dedicated variant workflow even when only stock or
  backorder changes; unit-test that it updates the target variant without a
  product deep update, then check all sibling variants and links on a copied
  DB. Create a new variant through its dedicated workflow and check that its
  inventory item/link and level exist. A previously orphaned
  inventory item with the same SKU is not proof of BAS ownership: refuse an
  automatic claim by SKU and investigate it separately. Compare relevant
  values before updating, since unconditional upserts flood subscribers with
  change events.
- Check port listeners before starting another dev process; avoid duplicate
  servers that obscure which build is being tested. Verify with lint,
  `tsc --noEmit`, tests, and a response from the intended process.
- `mattpocock/skills` (`grilling`, `grill-me`) plus `impeccable` and
  `ui-ux-pro-max` live in `.claude/skills/` inside the Barvex repo, not in the
  Hermes profile — `skills_list` will not show them; read the files directly.

## Architecture docs live per folder

The repo carries `ARCHITECTURE.md` in each significant folder: root (data flow,
decision table, index of the rest), `apps/backend/`, `apps/backend/src/modules/`,
`modules/bas-sync/`, `modules/nova-poshta/`, `apps/storefront/`, `src/lib/`,
`src/modules/`. Read the root one first — it indexes the others — then the file for
the folder being changed, and update that file in the SAME commit as a change that
moves a boundary, adds a module/job/workflow/route, or overturns a listed decision.
Procedure and format rules: skill `architecture-documentation`.

The repo's `CLAUDE.md` is write-protected: a non-interactive edit to it is refused by
design. Hand the user the snippet to paste rather than retrying or routing around it.

## Not in scope of the current contract

Site orders flowing back to BAS is a separate second stage. Never sync carts,
logins, addresses, reviews, sessions, payment data or Medusa-internal ids.
