# Mutation-checking a test suite

A green suite proves the tests ran, not that they constrain anything. Several
tests can pass against deliberately broken source. Mutation checking is the cheap
answer: break the code on purpose, confirm the tests go red. A surviving mutant
marks a test that asserts nothing useful.

Run it whenever a suite is the main evidence of correctness — a pure logic core, a
privacy/consent boundary, a serialization contract, a scheduling or pricing rule.

## Procedure

1. Copy the repo to scratch; never mutate the working tree, because an interrupted
   run leaves sabotaged source behind that reads like real code.
   ```bash
   cp -r <repo> "$TMPDIR/mutcheck" && cd "$TMPDIR/mutcheck" && rm -rf .build
   ```
2. Back up each file you will mutate (`cp $f $f.bak`) and restore from the backup
   after every mutant; in-place reverse edits drift.
3. One mutation at a time: apply, run the suite, record the failure count, restore.
   Script the loop, and make a missing anchor string `assert` loudly — otherwise
   you record a "survivor" for an edit that never applied.
4. Mutate the claims, not random tokens. Highest-yield targets:
   - invert or delete a guard (`consent.allowsScanning` → `true`)
   - swap an enum case in a predicate (`.revocation` → `.consent`)
   - empty a payload the code claims to carry (`signals: signals` → `signals: []`)
   - hardcode a flag the caller chose (`sharesSupportingPhotos:` → `true`)
   - move a boundary (`>=` → `>`, `+1` → `-1`)
5. Fix each survivor by strengthening the test, then re-run that mutant to watch it die.
6. Budget time: a full `swift test` per mutant plus a cold `.build` is minutes, so
   run the loop as one background script over a handful of targeted mutants rather
   than interactively.

## Equivalent mutants

A survivor is not automatically a test gap. If the mutated state is unreachable,
the mutant is *equivalent* and no honest test can kill it. Before writing a test,
prove reachability by finding a caller path that produces the state. Typical case:
a constructor already rejects the bad input, so a downstream re-check looks dead.

When it is genuinely unreachable, keep the defensive code and comment that the
check is deliberately redundant plus which future path (cloud rehydration,
deserialization, a second initializer) would make it load-bearing. Do not delete
it, and do not fake the state through `@testable` internals just to get a kill —
that test passes forever and documents nothing. Report it as an equivalent mutant,
not as a closed gap.

## Test shapes that survive mutation

- **Absence plus fidelity.** A boundary test asserting only that forbidden fields
  are missing also passes when the payload is emptied entirely. Pair every
  "field X is absent" with "field Y round-trips to the value it went in with".
- **Hostile fixtures, not polite ones.** Probe user-facing text with one string
  carrying every sensitive shape at once (asset identifier, coordinate pair,
  account, record key) and loop the assertions over a list of failures.
- **Distinctness, not just presence.** Per-item assertions (`code` is non-empty)
  pass against a constant; add `Set(codes).count == codes.count`.
- **Step-by-step invariants.** For a readiness flag, assert false at every prefix
  of the setup and true only at the end. A single end-state assertion survives
  replacing the whole predicate with `true`.
- **Parameterized over the knob.** Loop a limit across its range and assert the
  invariant each time; one hardcoded value hides the off-by-one.
- **Identity of derived output.** For map points, matches, or rows: assert side,
  value, and key per element, not just `count`. A count check passes with every
  coordinate zeroed.
