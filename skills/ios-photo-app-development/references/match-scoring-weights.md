# Weighted match scoring and the reach gate

When the product has an opinion about which coincidences matter more ("the same
hour a few streets away beats the same doorstep months later"), that opinion
must be a stated weight, not a sort order.

Two mechanisms, never collapsed into one: a **gate** decides which pairs are
matches at all, and **weights** rank the survivors. Build both. A weight can
only push a weak match down the list, so a list of coincidences ranked perfectly
is still a list of coincidences — and where each surviving match releases a
photo, how loose the gate is was a disclosure decision wearing a ranking
costume.

## Why a comparator is the wrong shape

A lexicographic sort — kind first, then distance, then day gap — encodes the
trade-off as an unconditional precedence. Same-day then beats same-place
*always*, so a photo pair 2 km apart on one afternoon outranks the identical
paving stone a day later, and no caller can change it. Replace it with per-axis
scores plus weights.

## Shape that works

- One criterion per axis (clock-time proximity, day alignment, place
  proximity), each scored `0...1` by smooth exponential decay
  `exp(-value / halfLife)`. Decay is monotone, so a worse value on one axis can
  never raise a total.
- Normalise weights to sum to 1 on construction. Otherwise an "important"
  variant merely produces bigger numbers, and any threshold tuned against one
  variant is meaningless against another. Normalisation also makes the weights
  scale-invariant, so `2:1:1` and `50:25:25` rank identically.
- Reject negative weights (one axis cancelling another lets an encounter score
  below one that is worse on every axis), non-finite weights, all-zero weights
  (every score becomes 0 and ranking silently degrades to scan order), and
  non-positive half-lives.
- Return the per-axis breakdown alongside the total. A single blended number is
  not reviewable: when a result ranks surprisingly high, the breakdown is the
  only way to tell a real finding from a weighting mistake.
- Ship a few named variants plus a list of all of them, so they can be measured
  against one fixture rather than argued about.

## The gate: one radius per time band, plus a hard horizon

A single flat radius cannot state the product's central claim. At the same
moment, 1.5 km apart is a real near miss — both people were in that square and
might have passed each other. A month later the same 1.5 km is true of millions
of strangers who merely visited the city. Make the allowance a function of the
time gap: bands in ascending time order with non-increasing radius, each one a
sentence someone could defend out loud.

- Validate band ordering at construction — ascending time, non-increasing
  radius. Out-of-order bands make the lookup return a radius that depends on
  array order rather than on the gap, which surfaces as a mysteriously absent
  match rather than as a failure. Allow equal radii so a flat reach stays
  expressible for comparison against the old behaviour.
- Give the gate an explicit maximum day gap. Without it the furthest band is
  silently "forever" and two photos of one doorstep years apart still match,
  held off the top only by a decaying weight. That is not a weak match to rank
  low, it is not a match.
- Do not mistake a **presentation** cap for the gate. A "maximum days per
  chapter/story" bounds how long one *presented* unit may run and says nothing
  about the permissible gap between two photos — if the horizon is only ever
  enforced there, the gate has no horizon at all. See the segmentation rule in
  the parent skill.
- Keep day gaps graded rather than lumping every different-day pair into the
  last band, or a two-day gap gets the same allowance as a twenty-day one.
- Treat `maxDaysApart: 0` (same-day only) as a valid configuration, not an
  invalid one; only negative values are errors.

**Converting a coarse unit into a fine one for band lookup ties at the
boundary.** A one-day gap expressed in minutes is exactly 1440, so it lands
*inside* a "within 24 hours" band and inherits the allowance written for a pair
sharing one day. Different days is strictly the weaker claim and must never tie
with the band above it: skip bands at or below one day when looking up a
different-day pair, rather than nudging the converted value by one.

## Two decisions that are easy to get wrong

**Carry the clock gap as an optional, and ignore it across different days.**
"We don't know when" and "within the same minute" are opposite facts; a
zero default turns the first into the second. And comparing the same time of day
across distant dates scores a coincidence of routine as a near miss, so a
cross-day result must argue its case on day alignment alone.

But "different calendar day" and "far apart in time" are not the same fact, and
using day equality as the proxy for "same moment" throws away the midnight
case: photos at 23:50 and 00:10 are twenty minutes apart and score as if there
were no time evidence at all, while the identical gap at midday scores more than
twice as high. Where near misses are the product, define the shared-moment test
by elapsed clock gap with its own threshold (a few hours), and reserve the
day-alignment axis for gaps genuinely beyond it. Evening is exactly when people
cross paths in a city, so the calendar-day proxy discards the richest cases.
Probe the midnight pair explicitly before shipping either design.

**Drop an unavailable axis from numerator AND denominator; never score it 0.**
Zeroing punishes a result for a privacy choice — a pair who never shared capture
times would see every same-day result capped below a pair who did. Renormalising
over the available axes keeps a perfect score reachable.

## Tests that actually guard this

The existing suite passing unchanged after a comparator is replaced by scoring
is the alarm, not the reassurance: it proves no test ever covered the trade-off.
About eight tests cover the weighting, plus about six for the gate. Write only
these.

For the gate:

- The trade-off itself: a kilometre apart matches at the same moment and does
  not a month later.
- Each band binding at its stated distance — one loop asserting just inside
  passes and just outside fails. This is the one place a table-driven loop earns
  its keep, because every row is a separate product promise.
- The horizon: nothing matches beyond it however close the spot.
- A different-day pair not inheriting the same-moment allowance (the 1440-minute
  tie above).
- Closer day gaps getting a wider allowance than distant ones.
- Only the configurations that break the gate *silently*: bands out of time
  order and radius widening with time.

For the weighting:

- The product decision itself, as a direct comparison of two concrete results
  ("same hour a few streets away" beats "same doorstep months later").
- The case the old comparator made unexpressible — a same-day result across town
  losing to a next-day result next door.
- The inverse variant genuinely inverting that order, not just shuffling ties.
- Clock time separating two same-day results, and being ignored across days.
- The strictest shipped variant actually being stricter than the default on the
  same input.
- Only the weight validations that break ranking *silently*: a negative weight
  (one axis cancels another) and all-zero weights (ranking degrades to scan
  order). A non-finite weight or a bad half-life throws loudly, so one combined
  test is enough.
- Deterministic tie-breaks on stable identifiers: library enumeration order must
  not change which result is "closest", or the same library ranks differently on
  two runs.
- An end-to-end assertion that different variants promote different top results,
  so the weighting is not cosmetic.

Do **not** test monotonicity across the shipped variants, symmetry of the time
gap, scale invariance, that a perfect result scores exactly 1, that scores stay
within `0...1`, that the weights sum to 1, or that ranking an empty list returns
an empty list. Each of those asserts a property of `exp()`, `abs()`, a division,
or `sorted()` — not a decision this product could get wrong — and the
variant-looped ones are large, slow to read, and crowd out the eight above.
State in the test file's doc comment which properties were deliberately left
untested and why, so the next session does not re-add them as "missing
edge cases".

## Guard the fixture itself

In an all-pairs matcher, every A signal pairs with every B signal. Place fixture
points so that unintended cross-pairings exceed the radius filter — a tie broken
by identifier on co-located fixture points is the usual first symptom that they
do not. Assert the intended pairs by name inside the comparison test that already
reads them, rather than as a separate fixture-shape test; a standalone test that
only restates the fixture is one more thing to maintain for the same coverage.

**Tightening a gate silently changes what older ranking tests measure.** A
fixture built for a loose radius can place its "same day but further" point
outside the new gate, so the test still passes while now asserting the gate
instead of the ranking it is named for. When a gate narrows, re-read every test
whose name mentions ranking or precedence, move the fixture point inside the new
allowance, and say in the diff that the fixture moved and the claim did not.
