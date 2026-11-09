# Cutting a quadratic pairing step without changing the findings

Applies once measurement has shown the pairing cross product is the hot term
(see `references/matching-performance-measurement.md`). The danger here is not
slowness, it is **silently losing real matches while every test stays green**.

## The optimisation

Bucket one side's stays into a grid whose cell size is the widest radius the
gate can allow, then consider only the nine cells around each stay of the other
side. Pairs more than one cell apart in either axis cannot be within that
radius, so they were only ever being measured in order to be discarded.

Rules that make it correct:

- **The index is an index, never a filter.** It returns a *superset*; every
  candidate still goes through the unchanged gate. Anything else converts a
  performance change into a change in which findings exist.
- **Scale longitude cells by the row's latitude** (`cell / max(ε, cos(lat))`).
  A fixed longitude width is correct but needlessly wide far from the equator —
  slow exactly where it should help — and scaling the wrong way drops real
  neighbours. The floor keeps cells finite near the poles.
- **Offer a candidates-without-distance call** alongside the exact one. The
  caller usually needs the distance anyway, and computing it in both the index
  and the loop doubles the only genuinely expensive arithmetic.

## One index per allowance, not one for the widest

The decisive win, and easy to miss: where the gate's radius varies by time gap,
a single index sized to the *largest* radius does the widest possible search to
settle the tightest possible claim. Same-day pairs may be allowed kilometres
apart while a cross-day pair must be within a couple of hundred metres — and
over any period longer than a day, nearly every pair is a cross-day pair.

Build one index per allowance class (same-day, keyed by calendar day; cross-day
at the tight radius), union the candidate sets, and de-duplicate by id because
the classes overlap. Expose the tight bound from the gate itself
(`radiusMetres(1, null)`) rather than recomputing the band table at the call
site. Measured effect of the split alone: a 4× improvement became ~40×.

## Proving the findings did not change

**A fixture run through the new code twice proves nothing.** Comparing the
optimised builder against itself and diffing the output is a self-comparison
that passes unconditionally; it is the easy mistake and it feels like evidence.

The real check, scriptable and cheap:

1. Write a throwaway script that prints a canonical fingerprint of the full
   output — per chapter, the city and every encounter's id pair, rounded
   distance, day gap, minute gap, kind — as one JSON line.
2. Run it on the working tree, redirect to a file.
3. `git stash -q`, run the *same* script against the pre-change code, redirect
   elsewhere, `git stash pop -q`.
4. `diff` the two files. Identical output is the claim; anything else is a
   behaviour change to explain.

Sweep shapes that exercise the geometry, not just the happy path: mixed and
full overlap, a high latitude (~70°N) where longitude cells stretch, the
equator, the date line, a tight all-same-day window, and a sparse year.

## Test shapes that catch the real failure

The failure mode is not a crash — a dropped neighbour reads to the user as
"you two never crossed paths". So assert *agreement with exhaustion*, not
result counts:

- For every point in a random cloud, the indexed lookup equals a brute-force
  scan filtered by the same radius.
- A neighbour at high latitude is still found (guards the longitude scaling).
- The index actually divides the work: assert the cell count is far above 1, or
  a single bucket holding everything would be "correct" and useless.
- A pair that **only the loosest same-day band allows** (e.g. 1.2 km, 25 min
  apart) is still reported. This is precisely the pair a single tight index
  loses.
- Guard against a vacuously fast matcher: assert the found set is non-empty, or
  every other assertion passes when the search returns nothing.

## Commit message

Record the before/after table, the fixture shape, and that the gate is
untouched with the equivalence method named. Without it, the two-index split
looks like redundant complexity and gets collapsed back into one.
