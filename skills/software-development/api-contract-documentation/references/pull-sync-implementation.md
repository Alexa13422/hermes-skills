# Implementing the consumer side of a pull sync

The contract says what the provider exposes; this is the code we write to walk
it. Read alongside `references/erp-sync-contracts.md`, which defines the
envelope this implementation consumes.

Build it as layers that can be tested without a provider: a state store, an
HTTP client, pure mappers, then the worker that drives them. The first three
need no database and no network, so they carry essentially all of the test
coverage. Write the worker last — it is the only layer that mutates the
catalog, and the decisions it needs (what to do with an upstream deletion whose
records are referenced by existing orders) are the user's to make, not yours.

## State store

One row per resource (`products`, `inventory`, `categories`, `brands`) holding:
the in-flight `cursor`, the `watermark` to send as the next run's
`updated_since`, the provider's `snapshot_at`, a status, counters, and a
`run_id` + `locked_at` pair for the lock.

- Advance the watermark **only** in the success path, never on checkpoint and
  never on failure. A failed run must keep its cursor so the next attempt
  resumes mid-walk instead of restarting or, worse, skipping ahead.
- Expire a stale lock on a timeout (`locked_at` older than ~30 min), or a
  process killed mid-run blocks the resource permanently.
- A status check followed by a separate status write is **not** a lock — two
  scheduled runs read `idle` in the same instant and both proceed. Take the
  lock in one conditional write, or wrap the run in the framework's own
  distributed locking module when the project already depends on one.

## HTTP client

- The base URL env var must hold the **full** versioned path, because the client
  concatenates endpoint paths onto it. Say so in the env template with a worked
  example — a host without the version prefix yields `404` on every call, and
  the symptom points at the provider rather than at our config.
- Retry only `429` and `5xx`, with exponential backoff plus jitter, a cap on
  attempts **and** a cap on total elapsed retry time. Honour `Retry-After`,
  parsing both the seconds form and the HTTP-date form. Never retry other `4xx`:
  they are contract violations that will not fix themselves.
- Map `410` to its own error type so the worker can restart the walk from the
  stored watermark instead of treating an expired cursor as a transient fault.
- Give every request a timeout via `AbortSignal`; a provider that accepts the
  connection and never answers otherwise hangs the scheduled job forever.
- Validate each response against a schema derived from the contract and name the
  resource plus the first offending field in the error. An unvalidated envelope
  turns a provider-side field rename into a confusing mapper crash much later.
- The pagination helper must refuse to loop forever: stop when `next_cursor`
  repeats or is absent, and treat `has_more: true` with an empty `items[]` as a
  provider fault rather than a reason to request the same page again.
- Throw the framework's own error class where one exists; a bare `Error` is
  often rewritten to a generic message by the HTTP layer and the real cause is
  lost.

## Mappers

Keep them pure — no fetches, no container lookups, no workflow calls — so the
whole field contract is testable in milliseconds.

- Return a result object (`{ok: true, value}` / `{ok: false, errors}`) instead of
  throwing per record. The worker then quarantines the bad record and finishes
  the pass, rather than one malformed row aborting a catalog-wide sync.
- Convert minor units with integer arithmetic and test a value that does not
  divide evenly (`18599`), plus `0` and a large value.
- **A mapper that returns a whole `metadata` object wipes manual fields.** Even
  when the mapper never sets the manually-curated keys, an upsert that assigns
  the returned object replaces the stored one, so ingredients, usage text and
  anything else typed into the admin disappear on the next sync. Merge into the
  existing metadata, or restrict the write to the keys the sync owns, and assert
  that in a test.
- The same applies to any set-valued relation: a tag write that replaces the
  full set removes tags another process owns. Read the current set, add or remove
  only your own member, write back.
- Filter out values the app computes for itself even though the provider sends
  them, and assert the exclusion in a test — otherwise a feature silently loses
  its data to the sync.
- Resolve the deletion status to an intent (`publish` / `unpublish` /
  `soft_delete`), never to a physical delete. Order lines reference variants; a
  hard delete either breaks order history or leaves dangling references, and
  neither is recoverable.

## Verification

Name unit tests with the suffix the project's test script actually globs, and
run workspace test scripts from the repo root so the declared dev dependencies
resolve — running them from the package directory fails on a missing runner
binary and looks like a broken environment.

A passing suite written by the same pass that wrote the code proves little when
the test and the implementation disagreed at some point: confirm the expected
values against the contract file, not against the implementation.
