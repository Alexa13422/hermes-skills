---
name: api-contract-documentation
description: "Document an existing API as a handoff contract."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [openapi, swagger, api-docs, data-contract, integration, handoff]
    related_skills: [codebase-inspection, demo-deployment-readiness, grounded-citations]
---

# API Contract Documentation

Reverse-engineer what an app's API surface actually is, then ship it as docs a
third party can act on — typically an integrator, a DBA, or whoever fills the
database or builds the sync on the other side.

## When to Use

- "зроби API-шку / док по ендпоінтах", "like that Java thing that shows all the endpoints" (= Swagger UI)
- Someone outside the repo must build against, populate, or sync with this app
- You need to state which fields the frontend truly requires, and where they come from

**Not for:** auditing code quality (`repo-quality-audit`) or making the repo
installable (`demo-deployment-readiness`).

`references/erp-sync-contracts.md` — depth for accounting/ERP integrations
(BAS, 1C, SAP): ownership split, the two-identifier rule, pull- and push-model
mechanics, and what must never be synced into the storefront.

`references/pull-sync-implementation.md` — writing the consumer side once the
contract is agreed: state store and locking, client retry/timeout rules, pure
mappers, and the metadata-overwrite trap that silently erases manual fields.

## Core rule: the consumer code is the spec, the framework docs are not

What the site *needs* is what the site *calls*. A framework's published Store
API lists dozens of routes the app never touches, and omits the custom ones that
matter most. Derive the list from the client, then verify each path against the
installed framework — never from an SDK method name, which does not mirror its
route (`sdk.auth.verification.request` hits `/auth/verification/request`, not
`/auth/<actor>/<provider>/verification`).

## Step 1 — Extract every call the client actually makes

Two populations, both needed: literal route strings and SDK method calls.

```bash
cd <client>/src
grep -rhoE '"/(store|auth|admin)/[^"]*"' --include=*.ts --include=*.tsx . | sort -u
grep -rhoE 'sdk\.(store|auth)\.[a-zA-Z.]+' --include=*.ts --include=*.tsx . | sort -u
```

SDK calls resolve to paths you cannot grep for. Resolve each one against the
installed framework's route tree, which encodes the real path shape:

```bash
find node_modules/@scope/pkg/dist/api -type d | sort
```

Also capture the custom routes the project added itself (`src/api/**/route.ts`
or equivalent) — these are the ones no public documentation will ever cover, and
they deserve a `[custom]` vs `[framework]` marker on every operation so the
reader knows what is negotiable.

## Step 2 — Mine the field contract from the mapper, not from the model

The database model lists what *can* be stored; a frontend mapper/util layer
lists what is actually *read*. That file is the contract. Pull from it:

- the exact `metadata` keys the UI consults (anything else is ignored)
- named constants for thresholds, and reuse the number, do not restate prose
- exact-match strings the UI compares against

Exact-match values are the silent breakers — record them verbatim with a warning.
An option whose title must be exactly `Об'єм`, or a flag checked with `!== true`
so the string `"true"` fails, produces no error and no data. State the required
type and literal, and that a near-miss fails silently.

Grep the repo for each flag before describing it — a root `AGENTS.md` or similar
often states the project's own rule for when it may be set, and the doc must
agree with it rather than invent a looser one.

## Step 2b — Settle the sync DIRECTION before writing a line of spec

Who initiates is the first architectural question, not a formatting detail. Ask
it explicitly before drafting: does the external system expose an API we poll,
or does it push to endpoints we must build? Writing the wrong direction wastes
the whole spec — paths, verbs, request bodies, and auth all invert.

The deciding question for the integrator is one sentence: *can you expose an API
on your side, or is it easier for you to send HTTP requests to ours?* An ERP/
accounting vendor (BAS, 1C, SAP) usually prefers exposing a read API, because
outbound scheduled HTTP from inside the accounting system is the harder sell.

Two valid shapes, and they are not symmetric:

| Direction | Shape | Requires |
|---|---|---|
| We pull (they expose) | `GET` endpoints on THEIR server, we schedule the fetch | opaque `cursor` + `next_cursor` + `snapshot_at` (never `page`), `updated_since` as an inclusive UTC lower bound, `updated_at` on every object, an explicit `status: deleted` tombstone |
| They push (we expose) | `POST` endpoints on OUR server, queued async | `Idempotency-Key` per batch, `job_id` + status endpoint so the sender sees real results instead of a bare 200 |

## Step 2b-bis — Specify the pull envelope as cursor + snapshot, never page numbers

Offset pagination is wrong by default on a live dataset, so do not offer `page`
as an option the integrator may pick. While the consumer reads page 1 someone
edits a row, the ordering shifts, and page 2 returns one record twice and skips
another — with a `200` and no error, so nobody learns the record never arrived.
Require instead:

- an opaque `cursor` query param fed from the previous response's `next_cursor`
  (`null` when the walk is done), over a provider-guaranteed stable sort such as
  `(updated_at, external_id)`;
- `snapshot_at` — one fixed instant for the whole walk, identical on every page,
  so the data cannot drift between requests;
- `updated_since` as an RFC 3339 **UTC** bound with an explicitly **inclusive**
  comparison, and dedup on our side: `>` drops records sharing a timestamp,
  `>=` duplicates them, and only one of those is recoverable;
- a rule that a `cursor` in the request makes `updated_since` moot, so the two
  cannot disagree about where the walk starts;
- `410` + `cursor_expired` as the contractual way to say "restart the walk";
- `total` explicitly optional and nullable, since an exact count is often the
  single most expensive part of the query and nothing should depend on it.

Advance the stored watermark to `snapshot_at` only after the final page lands.

When the user asks why pagination exists at all, answer with the failure, not
the convention: one JSON of a whole catalog is tens of MB, which times out, is
lost entirely on a dropped connection, and is held in memory on both ends.

State the direction in the title and the first paragraph of both the spec
`info.description` and the HTML lead (`BAS → Barvex`, "they expose, we fetch").
A reader who guesses the direction implements the mirror image of the contract.

When you invert an existing spec, delete the artifacts of the old direction
wholesale — a leftover `Idempotency-Key` row, `job_id`, or a `POST` badge in a
pull-model doc reads as a second, contradictory protocol. Grep the rendered file
for the dead tokens afterwards rather than trusting the diff:

```bash
python3 -c "
import re
h=open('index.html').read()
print('POST' in h, 'job_id' in h, 'Idempotency' in h)
print(re.findall(r'class=\"path\">([^<]+)',h))"
```

## Step 2c — Spell out what travels on EVERY request

A per-endpoint list is not enough for the implementer: they need one table of
the constants that ride along on all of them, split by position — base URL,
headers, query params, and the response envelope fields. Then repeat, per
endpoint, which of those apply in one line (`Header: API key. Query:
updated_since, page, limit.`). Without the shared table each endpoint entry
either omits the auth header or restates it eight times.

Include the owning side's own schedule in the doc even though the other side
does not implement it (`/inventory` every 5–15 min, full catalog nightly) — it
is what tells the API owner what load to expect and whether to rate-limit.

## Step 3 — Label every field with its origin

For a handoff doc, "which field" is half the answer; "who fills it" is the other
half. Mark each row **(sync)** or **(manual)**, and name the one key the sync
matches on for idempotency. Without a stated match key the first re-run creates
duplicates instead of updates.

Call out fields that look cosmetic but drive money or logic — shipping weight and
dimensions feeding a carrier tariff, units that differ by 1000x between systems.
Name the configured default and whether the project overrides it, because a unit
mismatch is invisible until it is billed.

## Step 4 — Document what is declared but not wired

An endpoint the client calls but the backend cannot serve belongs in the spec
WITH its real current behavior, not omitted and not presented as working.
Verify against the project's own module config rather than framework defaults:

```bash
grep -n -i "payment\|i18n\|locale" <backend>/medusa-config.ts || echo "module absent -> confirmed"
```

A route missing from config returns empty or 404 regardless of what the framework
supports. Distinguish "framework route, module not installed" from "planned, not
built" — mislabeling core behavior as a project TODO sends the reader to build
something that already exists.

## Step 5 — Choose the page format: Swagger UI is often too heavy

Swagger UI is the default answer to "like that Java thing", but for a one-shot
handoff contract of under ~10 endpoints it reads as overloaded: collapsible
sections, a Schemas tree, and chrome that buries the five facts the reader
needs. Prefer a single hand-written static HTML page — header with the
direction, a flow strip, the shared-parameter table, a flat endpoint list, and a
key-field table — and keep the OpenAPI YAML beside it as the machine schema for
Postman/client generation. Reach for Swagger UI only for a large surface (tens
of routes) the reader will browse rather than read top to bottom.

Both formats must open on a double-click with no server: inline the CSS, use no
external fonts or CDN scripts as a hard requirement, not a nicety.

## Step 5a — Make the page teach the mechanism, not just list fields

The reader of a sync contract is implementing a protocol they have not seen
before, so a page of reference tables leaves them technically informed and
practically stuck. Lead with plain-language explanation and put the tables after
it. What earns its place:

- the loop in numbered steps ("the site asks what changed" → "the ERP returns a
  chunk plus a bookmark" → "the site keeps turning pages" → "the site saves the
  new starting point only after a clean full pass");
- a **why** section for every non-obvious design choice — why chunks instead of
  one payload, why a bookmark instead of a page number, what `snapshot_at` is
  for. Justify each with the concrete failure it prevents, not with a convention;
- a worked two-request example in a code block showing real values flowing from
  `next_cursor` into the following request;
- a callout box for each trap that fails silently: the deletion tombstone, the
  immutable-id rule, grams-vs-kilograms;
- a statuses/error table mapping each code to what the consumer does about it.

Plain-language framing beats precise jargon here ("a bookmark saying where I
stopped" for a cursor). The YAML next to it is the precise artifact; the page
exists to make someone able to build against the YAML.

## Step 5b — Build a self-contained Swagger UI (large surfaces only)

`templates/build-swagger-docs.py` is the generator; copy it next to the spec and
run it. Two non-obvious requirements it encodes:

- **Vendor `swagger-ui-dist` locally and EMBED the spec in the HTML** as a JS
  object. Opened over `file://`, Swagger UI cannot `fetch` a sibling
  `openapi.yaml` — CORS blocks it and the page shows only a resolver error. An
  embedded spec makes the file work on a double-click, offline.
- **Escape `</` as `<\/` in the embedded JSON.** Any `</script>` inside a
  description closes the tag early and blanks the page.

```bash
curl -sfL -o vendor/swagger-ui.css https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css
# + swagger-ui-bundle.js, swagger-ui-standalone-preset.js
```

Set `supportedSubmitMethods: []` to drop "Try it out" — a contract reference
that offers a dead request button invites the reader to debug the doc.

## Step 6 — Verify the page renders before claiming it works

A valid spec and a rendering page are different facts, and "PyYAML parsed it" is
neither. Run a real OpenAPI linter — it catches whole classes of damage a ref
check cannot see:

```bash
npx --yes @redocly/cli@latest lint openapi.yaml
```

Fix errors; `operationId`/`license`/4xx-on-health warnings are cosmetic and may
stand. Two error shapes recur and both parse as valid YAML:

- **An unquoted comma inside a flow map silently splits a field.**
  `description: Stable id, never changes` becomes `description` *plus* a stray
  key `never changes`. Quote any flow-map value containing a comma, or use a
  block scalar. Detect them mechanically — every stray key lands with a `None`
  value:

```bash
python3 -c "
import yaml
d=yaml.safe_load(open('openapi.yaml'))
def s(o,p=''):
    b=[]
    if isinstance(o,dict):
        for k,v in o.items():
            if v is None: b.append(p+'/'+str(k))
            b+=s(v,p+'/'+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o): b+=s(v,p+'/'+str(i))
    return b
print('stray keys:',s(d))"
```

- **`$ref` tolerates no siblings** — not `nullable`, not `description`, not
  `allOf` wrapping a single schema. When a reused type needs a nullable form or
  its own prose rule, declare a second named schema (`OriginalPrice` carrying
  `nullable: true` and the "must exceed price" rule) and `$ref` that instead of
  decorating the reference.

Then check refs resolve in both directions — a dangling ref breaks generation, an
orphan schema is dead weight that misleads the reader:

```bash
python3 -c "
import yaml,json,re
d=yaml.safe_load(open('openapi.yaml'))
s=json.dumps(d)
for g in ('schemas','parameters','responses','headers'):
    refs=set(re.findall(r'#/components/'+g+r'/(\\w+)',s))
    have=set(d['components'].get(g,{}))
    print(g,'missing',refs-have,'unused',have-refs)"
```

Then screenshot the real thing: Swagger UI paints via JS, so a headless capture
needs a virtual time budget or it photographs an empty div.

chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=1400,9000 --virtual-time-budget=18000 \
  --screenshot=/tmp/api.png index.html
```

Pick the window height from where content actually ends, then crop — a tall shot
is mostly blank and hides the tail:

```bash
python3 -c "
from PIL import Image; import numpy as np
a=np.asarray(Image.open('/tmp/api.png').convert('RGB'))
print('content height:',np.where(a.std(axis=(1,2))>2)[0].max())"
```

## Step 7 — Ship three files, not one

| File | Reader | Content |
|---|---|---|
| `index.html` | "show me the endpoints" | Swagger UI, grouped by tag, every op marked custom vs framework |
| `<PROJECT>-DATA-CONTRACT.md` | whoever fills the DB | Field tables with (sync)/(manual), match key, thresholds, exact-match gotchas, known limits |
| `openapi.yaml` | whoever edits it | The source; the HTML is generated from it |

**Commit the docs into the repo, then send the file.** A zip or chat attachment
is a delivery mechanism, not a home: artifacts written under `docs/` that never
reach a commit read to the user as "you built this somewhere else". Check and
close it out before reporting:

```bash
git status --short docs/api      # '?? docs/api/' means untracked, not saved
git add docs/api && git commit -m "docs(api): <contract> v<n>"
```

Say explicitly that the committed thing is documentation and that no endpoints
were implemented, then name what the implementation work actually is (sync
worker, cursor/watermark state table, external-id columns, idempotent upsert) —
otherwise a contract sitting in the repo is mistaken for a working integration.
Do not push to a remote without being asked.

While staging, drop file-sync debris from the doc directory (`*sync-conflict-*`,
`*.orig`); committing a stale duplicate of the README leaves two contradictory
navigation files in the handoff.

Add a short `README.md` saying which is which and the one command to rebuild.
End the contract doc with the source files it was derived from, so a future
reader can resolve a disagreement — the code wins, and they should know where it is.

## Pitfalls

- **Never infer a route path from an SDK method name.** Resolve it against the
  installed package's route tree or a verified doc page; method namespacing and
  URL structure diverge, and a wrong path in a handoff doc is acted on silently.
- **Flag server-side filtering the client fakes.** When a price or stock filter
  runs in memory over a capped page because the value is computed per-request
  and not stored, say so and recommend denormalizing it during sync. The DB owner
  is the only person who can fix it, and the doc is the only place they will learn it.
- **Write the spec from files you read this session.** Plausible field names and
  invented enum values are the main failure mode of a generated contract: the
  reader cannot tell them from verified ones and builds against fiction.
- **A pull-model spec needs an explicit tombstone, not just a hidden flag.** Use
  a three-state `status` (`active` / `hidden` / `deleted`) plus `deleted_at`, and
  an `include_deleted` param the consumer always sets. A record that merely stops
  appearing is indistinguishable from "unchanged", so a product deleted upstream
  stays on sale forever; `hidden` and `deleted` also need separating, because one
  retains the row and the other retires it. Allow a `deleted` payload to carry
  only the id, status and timestamps — demanding full objects for deletions makes
  the upstream side skip emitting them.
- **Money travels as an integer in minor units plus a `currency_code` field.**
  `{ amount_minor: 18550, currency_code: "UAH" }`, not a float and not a
  `price_uah` suffix: floats accumulate representation error on arithmetic the
  moment a discount or tariff is applied, and a name-encoded currency cannot be
  validated or extended. Keep the suffix convention for physical units
  (`weight_kg`, `length_cm`) where the value is not money.
- **State the cross-field rule next to a derived price.** A "was" price must be
  strictly greater than the current price or `null`; without the rule the
  storefront renders a strike-through "discount" that is higher than the sale
  price.
- **Replace free-text display values with a code + label + display triple.** A
  lone `"250 мл"` or `"7.0"` cannot be sorted, filtered or matched; ship
  `volume_value` + `volume_unit` (enum) + `volume_display`, and
  `shade_code` + `shade_label`. Same for tags: `{ handle, label, group }` with an
  immutable `handle`, because a renamed label otherwise mints a new tag and
  silently empties the filter that used the old one.
- **Never put localized UI text in an enum.** `[шт, уп]` is an interface string
  masquerading as a protocol value; use `sale_unit_code: piece|pack` plus
  `units_per_sale`, so packaging multiples are expressible at all.
- **Say whether each payload is a full snapshot or a patch.** State it once, in
  the schema description, and spell out that an empty array means "empty" rather
  than "unchanged" — otherwise every array field is ambiguous and a sync either
  never clears a value or clears all of them.
- **Gate required physical fields on a boolean the upstream side controls.** A
  `shippable: true` flag that makes `weight_kg` and all three dimensions
  mandatory is enforceable; marking them all nullable means the carrier tariff
  silently has nothing to compute from.
- **A contract needs a machine-readable error shape, not prose about retrying.**
  One `Error` schema (`code` enum, `message`, `retryable`, `request_id`), the
  full set of statuses on every protected operation, and `Retry-After` on `429`
  and `503`. "The client will retry later" in a description is not something a
  client can branch on.
- **Exclude data the app computes for itself.** A tag written by a backend job,
  or a counter derived from the app's own orders, must be marked do-not-sync —
  an incoming sync overwrites it and quietly breaks the feature that owned it.

## Step 8 — Critique the contract before the integrator does

A spec that validates is not a spec that works. Run two independent reviews in
parallel via `delegate_task` — they answer different questions and merging them
into one prompt yields a shallow pass on both:

- **Contract critic:** OpenAPI validity and ref resolution verified by script,
  type/required/enum sanity, ambiguities that break implementation (free-text
  values where an enum belongs, non-ASCII enum members, missing currency/units,
  absent error codes, retry and rate-limit policy, no deletion signal). Ask for
  findings graded blocker/major/minor with a concrete edit each.
- **Approach critic:** the architecture itself — clock drift and records that
  fall out of the watermark window, page-boundary races, detecting deletions,
  whether the source system survives the polling cadence, partial-batch
  recovery and idempotency on our side, cursor vs offset pagination, and whether
  a publish/validation stage is needed before the storefront shows synced data.
  Demand a verdict: OK / OK with conditions / change the approach.

Give each child the field conventions, project constraints, and absolute file
paths — they read from disk and must not edit the artifacts.

## Step 9 — Implementing against the contract

Once the contract is settled, the consumer side is a separate build: see
`references/pull-sync-implementation.md`. Two rules govern the handoff from doc
to code.

Build the layers that need neither network nor database first (state store,
client, pure mappers) and leave the worker that mutates the catalog until the
user has ruled on its destructive decisions. Shipping a tested read path plus an
unwritten write path is a better checkpoint than a complete pipeline the user
has not reviewed.

The contract file is the arbiter when code and test disagree. A suite that goes
green after a mismatch between an implementation and its test proves only that
they now agree with each other — re-read the spec to find out which side moved.

## Report style

Stay silent while working — no step-by-step commentary. Close with the artifacts,
then the handful of findings that change what the reader will do: the direction,
the match key, the exact-match traps, the unit risk, and anything
declared-but-not-wired. Short labeled bullets, no tables. Flag honestly which
claims are verified by execution (the render, the ref check) versus read from code.

When the user asks a conceptual question mid-build ("how do the headers work",
"who calls whom", "why two keys"), answer in prose and short snippets only —
do not rebuild artifacts or produce a document in response. They are checking
their own mental model, and an unrequested regeneration buries the answer.

## Pitfall: write_file refuses on files you only patched

A full rewrite of an artifact you previously created but have only `patch`ed
since is blocked as a stale write, and a paginated/truncated `read_file` does
not clear it either. To replace a spec wholesale, write the new content to a
sibling path and `mv` it over the target; for anything smaller, patch in place.
