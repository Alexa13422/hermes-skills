# Running a real verification stack for BAS sync

Depth for the "Where to run a verification stack" section of SKILL.md. Read
this before any run that writes to a real database.

## Where the stack lives

The dev Pi runs the editor, the agent and the already-live `npm run dev`, and
typically has only a few hundred MB free (`free -h` before deciding). Unit
tests and short-lived probes are fine there; a Postgres, a full backend or a
storefront is not — the owner has said so directly. Put the stack on the
Windows PC over Tailscale, which has Docker, and reach the UI from the Pi's
browser tooling. Check reachability first: `tailscale status` reports that host
as `offline, last seen Nm ago` when it is asleep, and SSH just times out. When
the PC drops mid-task, report the live-run step as deferred rather than
implying it passed — code and unit results stand on their own.

Run `db:migrate` and the sync on the machine hosting the database, not across
the link.

## The BAS stand-in

Use the smallest stand-in that serves the pull contract: static validated
fixtures for mapper/policy tests, or a dependency-free HTTP mock only when
checking client pagination, retries and the end-to-end pull. Do not build a
second full BAS application for verification — the owner has asked for a basic
version that answers the needed requests, nothing more.

The repo's HTTP fixture server is `apps/backend/scripts/bas-mock-server.mjs`;
use a changed snapshot phase to exercise a product and variant disappearing
without tombstones. Prefer a phase read from a file path in an env var
(`BAS_MOCK_PHASE_FILE`) so a phase switch needs neither a container restart nor
a new image.

Confirm the mock's *actual running phase* before each pass; its default or
leftover container configuration may already be the changed snapshot. Check how
it is wired with `docker inspect <container>` (network, bind mounts, cmd) before
assuming where its code lives.

When the contract changes, strip the removed fields from the mock too. A mock
still emitting a field the schema no longer accepts turns a successful
regression into a validation failure that looks like a code bug.

## Database discipline

For real writes, clone the existing Medusa database and run migrations and sync
against the clone only. Clone from the PRISTINE source every time with a
parameterised script plus an `.env` name guard that asserts the target name's
expected prefix and refuses to equal the production DB. Refuse to overwrite an
existing target.

An interrupted or failed sync can leave partially created products and price
rows despite an unchanged watermark: after fixing a write-path bug, rerun
acceptance on a NEW copy of the untouched source, not a previously failed
clone. Verify the source count separately before and after.

If Medusa has multiple stock locations, select the intended one explicitly with
`BAS_STOCK_LOCATION_ID` rather than guessing which receives an absolute BAS
quantity.

## Networking between WSL and Docker

When the CLI runs in WSL but Postgres, Redis and the BAS mock run in Docker
with published ports, point the TEST environment's service URLs to `127.0.0.1`
and confirm each published port; Docker service names resolve only inside their
Docker network. If the mock has no published port, expose it to WSL through a
small proxy on that Docker network, then verify an HTTP response before starting
Medusa.

If Medusa reports a database connection failure while a direct `pg` client
connects, compare the actual driver options and TLS negotiation before blaming
memory or network: Medusa may enable SSL for a non-local Docker host while
PostgreSQL does not accept TLS. For local-only Docker verification, disable SSL
conditionally through the project's explicit test setting; never switch it off
globally. Measure both direct `pg` and Medusa bootstrap, then rerun the
migration on the copied database.

Redis is optional for a verification run: the workflow-engine and locking
modules in `medusa-config.ts` are gated on `REDIS_URL`, so commenting it out
makes Medusa fall back to a fake instance (`redisUrl not found`) instead of
failing on `ioredis` connection errors. The locking module then disappears —
acceptable for a single-worker migration, not for exercising the sync lock.

## Remote execution mechanics

Put every remote SQL, grep or exit-code check in a `.sh` file and copy it over
rather than running it inline through SSH — inline quoting is reinterpreted by
the remote shell and fails in ways that look like application errors.

## What counts as acceptance

Run baseline, repeat baseline, changed snapshot, then baseline again; after
each, count successful/failed records, inspect state (`status`, cursor,
watermark), product/variant rows, inventory links and stock. A successful
process exit or `/health` does not prove the business state. Unit tests and a
backend `/health` response do not prove catalog upsert, metadata preservation or
storefront availability. Never call the sync complete until a real DB pass and
the relevant UI behavior have been verified.

Keep all credentials out of artifacts and reports; redact connection strings
and secrets. Read `.env` programmatically with an assert on the database name
and never print its values.
