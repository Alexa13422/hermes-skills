# Which assets count as evidence of a place

A photo library is not a location log. Several asset classes carry a coordinate
and a timestamp that are indistinguishable from a real capture once they reach
the matcher, so they must be excluded at the source, where the platform still
knows what they are.

## Exclude at the scanner, not downstream

Model asset kind explicitly (`photo` / `screenshot` / `notCameraOriginal`) in the
metadata DTO and filter before building a signal. Reasons:

- A **screenshot** has coordinates and a creation date like any photo. Nothing
  downstream can tell it was never a place the person stood; a screenshot of a
  map ends up asserting presence at the mapped location.
- A **non-camera original** (AirDropped, saved from a message or another app)
  carries the *sender's* coordinates. Treating it as the owner's places them
  somewhere they have never been.

Filtering later is not equivalent: by then the only remaining signal is a
coordinate plus a day, which is exactly what a genuine capture looks like.

## Duplicate collapsing

Identifier-based dedup catches only the same asset enumerated twice. The real
duplicates survive it:

- A **re-imported copy** (AirDrop to yourself, export-and-reimport, saved copy)
  gets a brand-new local identifier while keeping its capture moment and pixel
  dimensions. Key duplicates on `(capture second, rounded coordinate, pixel
  width, pixel height)`, not on the identifier.
- Round the components before hashing: time to the second, coordinates to ~1 m
  (e.g. 5 decimal places). A copy can differ in the last float digits without
  being a different photograph.
- Keep **pixel dimensions in the key**. Two captures of the same second at the
  same spot with different dimensions are a genuine second shot (another lens, a
  crop); collapsing them silently deletes evidence.
- A **burst** is one moment, not a dozen matches. When the platform exposes a
  burst identifier, keep the first frame and drop the rest.

## Count skip reasons separately

Return distinct counters — not-a-place, duplicate, unusable-metadata — rather
than one "skipped" total. The UI has to be able to say "40 screenshots were
filtered out" instead of implying an empty history, and a test asserting
`skippedUnusable == 1` for a duplicate is asserting the wrong reason. Adding a
new counter will break existing tests that folded everything into one total:
that break is the signal to make each assertion name its actual reason.

## Pitfall

These fields arrive from fixtures until a real platform adapter exists. Asset
kind, burst identifier, and pixel dimensions coming from test doubles proves the
filter logic, not that the platform reports them the way the fixtures assume.
Say so when reporting status.
