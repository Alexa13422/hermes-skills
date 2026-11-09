# Measuring what the matching pipeline actually costs

The scan runs while two people wait, on both phones, over libraries of tens of
thousands of photos. "Feels fast on my fixtures" is not a measurement, and the
shape of the fixture decides whether the number means anything at all.

## The finding that reframes the problem

**Cost is driven by how much the two people overlap, not by library size.**
Pairing is a cross product within each segment, so two people in the same city
every day are quadratic in the number of distinct stops, while two people who
rarely coincide stay near-linear. The better a pair matches the product's
premise, the worse the app performs — the worst possible shape of slowness, and
invisible to any fixture where the two libraries mostly sit in different places.

Measure an **overlap sweep**, not a size sweep. At minimum: a light overlap
(~⅓ of days shared) and a full overlap (same city every day) at each size.
Reporting only the light case is a methodological error, not an omission.

## Fixture rules

- **Shoot in bursts**: a handful of spots per day, several photos minutes apart
  at each, long gaps between. Evenly spaced photos make the stay-clustering step
  look useless and the pairing step look far more expensive than it is.
- **Different "city" must mean different coordinates too**, not just a different
  grid cell id. The gate rejects on distance, so same-cell-far-coordinates (or
  the reverse) measures a path the product never takes.
- **Seed the randomness deterministically** (a small LCG) so two runs are
  comparable and a regression is attributable.
- Report the **median of ≥3 runs** and discard an untimed warm-up pass, or the
  first row pays for module loading and JIT warm-up.

## Separate the per-photo cost from the per-period cost

They scale on different things and averaging them hides the problem:

- **Per-photo preparation** (timezone + city cell) runs once per photo. On
  measurement it is negligible — a six-figure library resolves in well under a
  second of pure CPU — so do not optimise it on suspicion.
- **Pairing** runs once per period and is the only term that can explode.

A resolver that caches per grid cell must be measured **both ways**: a
travelling library is nearly all cache hits, uniformly random coordinates are
all misses, and the honest cost sits between. Reporting one of them alone
overstates or understates by an order of magnitude.

## Scaling a desktop number to a phone

State the multiplier applied (≈3× for a phone's JS engine versus a dev host) in
the output itself, and label the column an estimate. Never present a host
timing as a device timing; never quote a device timing you did not measure on a
device.

## Locating the hot step instead of guessing

1. Run the benchmark under `npx tsx --cpu-prof --cpu-prof-dir=<dir> <script>`.
2. Parse the `.cpuprofile`: sum `timeDeltas` per sampled node id, aggregate by
   `callFrame.functionName` + url, print the top self-time entries.
3. `require` is unavailable in the tsx/ESM script — a profiler package pulled in
   with `require` aborts the run. The flag needs no in-script instrumentation.

Then **count the work**, not just the time: call the clustering step directly
and print stops-per-side and stops², so the explanation is a number
("16k stops each → 255M pairs") rather than an inference from a flame profile.
Attributing the cost to the wrong layer (geography, string formatting) is the
normal mistake; the day/distance helpers merely show up because the cross
product calls them millions of times.

## Reporting to this user

Lead with the number table, then the one bad case, then the mechanism in one
sentence. Present the negative result plainly — a disproven "this is fast"
is progress. Give the fix options as a short choice (cut the cross product with
a spatial bucketing pass; stream results oldest-last so the first findings
appear immediately) and ask which to do first; do not start optimising unasked.
No identifiers in the prose.

## Keep the benchmarks in the repo

Commit them under `scripts/` with a doc comment stating what the fixture shape
imitates and why, plus the lab→phone multiplier. A benchmark whose fixture
rationale is undocumented gets "simplified" into a uniform distribution by the
next session and silently stops measuring the quadratic case.
