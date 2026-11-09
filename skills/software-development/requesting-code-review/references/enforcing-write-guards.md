# Reviewing and building server-side write guards

For any rule of the form "this record may only change through the approved path"
(publication, quarantine release, ownership, price release).

## Leave a legal path open

Deny rules keyed on *ownership* ("record is managed by the integration") deadlock
legitimate work: the operator can no longer act and the privileged path refuses the
record because it lacks the quarantine marker. Key the deny on the *state marker the
guard itself sets*, and for every legitimate state enumerate the one allowed
transition out of it before approving the guard. Any state that both the ordinary
path and the privileged path reject is a bug, not safety.

Corollary: every code path that *enters* the restricted state must set the marker —
including the create path, not only the update path. A restricted record without the
marker is invisible to the release tool and blocked by the guard.

## Enumerate writers, not routes

Before accepting a guard, list every writer of the field: the single-record route,
the batch route, import/CSV routes and their confirm step, delete routes, cron jobs,
seed/maintenance scripts, and direct workflow calls from code. A guard on one route
proves nothing about the others. Validate the whole request *before* mutating:
a mixed batch containing one forbidden item must reject in full.

An after-update hook or an entity-updated subscriber runs after the write and cannot
prevent it — enforcement must sit before the handler, or in a shared guarded service
every writer is routed through.

## Framework routing pitfalls

- A parameterized matcher (`/resource/:id`) also matches sibling static paths
  (`/resource/batch`), so both guards run and the parameterized one looks up a
  nonexistent id and fails every request to the static route. Skip the reserved
  segment explicitly instead of relying on registration order.
- Tests that register middleware by hand in array order bypass the framework's route
  sorter and pass under either order, so they cannot catch an ordering regression.
  Build the chain through the framework's own sorter, and assert the guard was
  *skipped* — not merely that the request succeeded.
- Guard against a missing path parameter; a future registration on a non-parameterized
  matcher otherwise throws inside the guard.

## Read-then-write races

A guard that reads state, then calls `next()`, holds nothing: a concurrent sync can
change the record between the check and the mutation. The guard, the privileged
release path, and the background sync must take the same record-scoped lock around
the entire read-decide-write span. In-memory locking providers are single-process
only, so a multi-worker deployment needs a shared provider before the lock means
anything.

## Approval bar

Unit tests over the guard function prove shape, not enforcement. HTTP behaviour,
route registration order, and lock contention require an integration test against
the running service. Report unit-only results as provisional and keep the ticket open.
