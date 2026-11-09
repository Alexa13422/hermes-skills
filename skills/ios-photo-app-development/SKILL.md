---
name: ios-photo-app-development
description: Use when building PhotoKit iOS apps with shared results.
---

# iOS photo-library applications

## Procedure

1. Define the product claim before coding: distinguish evidence inferred from photo metadata from proof of presence, proximity, or meeting. Agree on the time/location threshold and what photos the other participant can see; record decisions before agents split implementation.
2. Design the permission flow: explain the purpose and sharing scope before requesting PhotoKit access. Request library access on a user action, handle full, Limited, denied and revoked states, and never describe a Limited scan as complete. Use `PHPicker` for explicit selections, not as a substitute for automatic full-library enumeration. Historical photo analysis does not itself require live Core Location permission.
3. Index `PHAsset.creationDate` and `location` locally first; both may be absent or inaccurate. Avoid downloading originals merely to discover candidates. Handle iCloud-backed assets asynchronously when a user actually needs a preview. Keep `localIdentifier` on the owner's device.
4. Separate the pure matching core from PhotoKit, city resolution, transport, and UI. Feed the core canonical city IDs and an explicit timezone; do not infer cities from raw coordinates inside a supposedly pure matcher. Test calendar-day boundaries, invalid/missing GPS/date, duplicates, symmetry, stable ordering, and intentionally broad matches. Label broad same-city/day results as *possible* overlap, not a confirmed encounter.
5. For a pair, establish separate identities and explicit pre-scan consent for any automatic sharing of supporting photos. Keep `PHAsset.localIdentifier`, raw coordinates, capture timestamps, and photo bytes on the owner's device; define a separate cloud DTO with opaque per-pair identifiers, coarse day/city signals, and no direct mapping back to local assets on the other phone. Test the serialization boundary, not only the in-memory matcher. Do not equate a celebratory reveal screen with a second consent gate. Provide unpairing and deletion of shared data. Confirm each phone's iCloud/CloudKit availability separately; iCloud Photos being off does not by itself establish that CloudKit is unavailable.
6. Implement the actual transport and invitation acceptance separately from the in-memory pairing state machine. For CloudKit, exercise owner private-zone sharing, the participant's shared database, retries/idempotency, pagination for record reads, and revocation behavior; a compiled `CKShare` flow does not prove two-device synchronization. Never assert CloudKit data is unreadable to Apple without validating the specific encryption and sharing model.
7. Divide implementation among agents by exclusive files/areas (matching core, UI, CI) and integrate centrally. Treat their verification claims as self-reports. Run the pure tests locally where a Swift toolchain exists and the iOS simulator build on a real macOS runner; inspect failures and repeat until the remote run succeeds. Then test pairing, permissions, and revocation with two real Apple IDs/iPhones. Simulator build is not TestFlight signing or on-device verification.

8. Review the core adversarially before extending it. Dispatch parallel reviewers
   (correctness, privacy/consent, test strength, product/architecture) and require
   each to prove every finding with a runnable probe in a scratch dir, commit
   nothing, and modify no files. Then reproduce each claim yourself with your own
   probe before touching source: a confident report citing exact line numbers is
   still often wrong about behaviour, and "fixing defensively" against a bug you
   could not trigger adds untested branches. Drop findings you cannot reproduce
   and say so.
9. Mutation-check the suite guarding the core and the transport boundary before
   trusting a green run as evidence — see `references/mutation-checking-tests.md`
   for the loop, the high-yield mutations, and the test shapes that survive them.
10. When the product needs media to cross the privacy boundary at all, model it as
   an enumerated release rather than a permission — see
   `references/media-sharing-boundary.md` for the type shape, the upload gate, and
   the rules that keep a feature from becoming library access.
11. When a screen's identity rests on a photoreal/animated art object (cloud
   shade, sky, iridescent rim), use the `mobile-ui-visual-assets` skill for the
   source decision, generation rules, licensing, and the animation budget.
12. Filter the asset source before it reaches the matcher: screenshots and
   non-camera originals are not places, and re-imported copies and bursts are not
   separate moments. See `references/metadata-source-hygiene.md` for the asset-kind
   model, the duplicate key, and why per-reason skip counters matter.
13. Persist the pair before building anything on top of it: a connection that
   dies with the process makes both people re-agree every launch, and sync has
   nothing to sync. See `references/persisted-pair-state.md` for the replay-not-decode
   rule, what must not be stored, and the store shape that stays testable on Linux.
14. When the product ranks coincidences by importance, express it as weights over
   scored criteria, never as a comparator's precedence order, and gate which pairs
   are matches at all separately from ranking them. See
   `references/match-scoring-weights.md` for the score shape, the per-time-band
   radius gate, the missing-data rule, and the tests that keep both honest.
15. Before answering "how does the ranking work now" or "what are the current
   thresholds", print the real curves and a worked ordering from the shipped code
   rather than reciting constants — see `scripts/rank-report-probe.md` for the
   throwaway-probe loop and the rule about deleting it afterwards.

## Presentation logic belongs in the core

- Model the reveal/paging order as a testable value type (which card is showing,
  what opens after the last one, what going back does), not as view state. On a
  machine with no simulator a view owning that logic can only be checked by hand
  on a device, so the product promise goes unverified; a core state machine is
  asserted in the same suite as the matcher.
- Let each stage ask the consent types what it may render rather than trusting its
  own position in the flow: the card asks the release for its media, the overview
  asks the precise-place agreement for its points. A stage that renders from its
  own state re-derives permission and will drift from the boundary.
- Scope a per-result map to the days of that result. Reusing the window-wide point
  set for a single card's "how close" view leaks the whole window into a view the
  user understands as being about one moment.
- Generate captions in the core and pin the wording with tests:
  - Never claim a meeting. Same-day proximity reads as "close enough to have
    crossed paths — not proof that you did"; different-day proximity must state
    plainly that the two were not there together. Assert the forbidden phrasings
    ("you met", "you were together") are absent from headline and detail.
  - Round distances to speech ("a few metres", "40 metres", "1.5 km"). A GPS fix
    is good to several metres, so a decimal metre is false precision dressed as
    accuracy; assert no caption contains a decimal point.
  - Never render an internal identifier in prose. A missing or blank place name
    falls back to words ("in the same city"), never to the city ID.
  - Fall back for blank display names instead of rendering ", was here" with an
    empty subject.

## Correctness rules for the matching core

- Order a day's signals by capture timestamp, with the identifier only as
  tie-break. Segmenting by calendar day alone makes every same-day multi-city
  trip collapse into arbitrary identifier order, and whole chapters vanish with
  no error.
- A presentation boundary must never decide which matches exist. Where pairing
  happens only *within* a segment (city span, chapter, page), the segment cut
  becomes a matching rule: a pair well inside the allowed gap is found or lost
  depending on whether an unrelated third photo opened the segment earlier. Carry
  recent signals forward across a length-driven cut, bounded by the gate's own
  horizon, and verify by building the same pair with and without an earlier
  unrelated photo — the result must be identical.
  - Anchor the length cut on the day the segment *opened*, stored explicitly, not
    on the first entry of its day list. Carried-in context would otherwise shrink
    the window each segment is allowed to cover.
  - Exclude carried signals from the segment's presented day range, or every
    segment after the first stretches back over its predecessor.
  - Skip carried-versus-carried pairs; that pair belongs to the previous segment
    and would be told twice.
  - Never carry across a category change (different city): it is a real break in
    the story, and carrying invents matches between places.
- Reject invalid metadata; never coerce it. Out-of-range or non-finite
  coordinates, blank ids and blank city ids get dropped, not clamped — a clamped
  point is rendered as a real place the person never stood in, and two clamped
  points rank as a perfect match at zero metres.
- Guard non-positive limits at construction. A zero "top N" yields a chapter whose
  own highlight is absent from its own list, so derived booleans (`hasSameDay…`)
  lie instead of erroring.
- Make a consent-derived permission unconstructible by a caller that did not earn
  it: a `struct` with a private init plus `from(consents:)`/`from(session:)`
  rather than a bare enum or bool, so the compiler, not a code reviewer, prevents
  a default-allow. Revocation must withdraw it too.
- Bound a proximity match by distance, not only by the coarse bucket it was
  grouped into. "Same city" grouping with no radius makes every pair of photos in
  the city an encounter, which silently drains any ranking built on it and, where
  encounters authorize sharing, promotes a whole city to a permission.
- Never swallow an invitation-acceptance failure with `try?`. The system has
  already consumed the share link by the time the callback runs, so a silent
  failure leaves the invited person tapping a spent link with nothing on screen.
  Publish the outcome as state, translate the platform error into the project's
  own failure wording, and retain the acceptance metadata so a network failure is
  retryable without a fresh invitation.
- Keep platform error text out of user-facing copy. It can carry an asset
  identifier, coordinate, account, or record key; put it in a separate
  `technicalDetail` field shown only behind an explicit "technical details"
  affordance, and assert in tests that the message does not contain it.

## Gates

- Before claiming an audited core "works", grep the app sources for the core's
  own symbols (session type, consent recorder, scan submitter, reveal entry
  point). A large green pure-test count says nothing about whether the UI ever
  calls that code; screens advancing on their own local view state while the
  state machine sits unused is the normal failure, and it looks identical to
  working from the outside. Report which stages are wired and which are still
  demo data, per stage.
- Replace a view-local boolean standing in for a recorded decision with a binding
  that reads and writes through the core. Key it on which side this device
  actually is, resolved from the session — a hardcoded first/second side reads
  the other person's answer on one of the two phones.
- Funnel every mutation through one place that catches the core's refusals and
  surfaces them. A swallowed refusal leaves the UI offering an action the core
  will reject.
- Keep build products out of the repository. Verify with a tracked-file count
  under the build directory before the first push, not after: once committed they
  conflict on every push and `git rm --cached` plus `.gitignore` is a second,
  noisier commit.
- Keep demo scans, mock pairing, and sample chapters visibly labeled as demo; distinguish a core protocol, a compiled platform adapter, a connected UI flow, and verified device-to-device behavior in every status report. Never present a UI prototype or simulator build as working photo access or sync.
- Do not `import` the core module from app-target sources when the generated
  project compiles those core sources directly into the app target. The types are
  already in that module, and the import fails only on the platform build — the
  local package test run stays green, so the breakage surfaces as a red remote run
  after the push. Check how the project generator lists the sources before adding
  an import to an app file.
- Check the remote run's actual conclusion and logs before saying a platform build passed. If a workflow push is rejected for missing GitHub `workflow` scope, add that scope through the approved authentication flow, verify `gh auth status`, push again, and inspect the run; a local YAML parse alone proves nothing.
- Keep the written product contract in step with the boundary the code enforces.
  A contract promising an exchange the transport cannot perform is read by
  reviewers and future agents as a missing feature, and it invites someone to
  "fix" it by widening the boundary.
- When the user asks what was left undone, answer in plain language: for each gap,
  what it means concretely, what the user would observe, and why it was left —
  not a restatement of the finding in the reviewer's vocabulary. End by naming the
  one decision you need from them.
- Report work the way this user wants it: no step-by-step narration while working.
  The final message states findings and outcome only — what was confirmed by
  reproduction, what was fixed, what survived as an equivalent mutant, and what
  remains unverified. Never relay a subagent's self-report as verification;
  re-check the commit, the CI conclusion, and the test count yourself first.
- Spend the test budget on decisions, not on arithmetic. Before adding a test,
  name the wrong product behaviour it would catch; if the answer is a property of
  `exp()`, `abs()`, `sorted()`, a division, or a constructor's own validation,
  skip it. Monotonicity loops across every shipped variant, scale invariance,
  symmetry, `0...1` range, empty-input, and single-element cases are the usual
  offenders — they read as thoroughness while asserting the standard library, and
  this user calls them spam. Roughly five to eight tests per new core module is
  the shape; record in the test file's doc comment which properties were left
  untested and why, so the next session does not re-add them.
- When pruning a suite, prune by that rule and commit the deletion on its own,
  with the commit body listing each removed test and the one-clause reason it was
  redundant. A bare "removed tests" commit is indistinguishable from weakening
  coverage to make a build pass.
- Prefer a vertical slice over more core tests once the pure core is well covered.
  A growing pure-test count validates assumptions, not platform risk (PhotoKit
  performance, city resolution, real two-device sharing); say so plainly instead
  of adding another core module.
- Keep the app repository separate from a source repository of copied engineering skills. Verify provenance and redistribution terms before making a repository with third-party skills public.
