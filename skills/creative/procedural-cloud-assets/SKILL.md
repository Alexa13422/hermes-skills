---
name: procedural-cloud-assets
description: Use when making animated cloud art. Procedural cumulus.
version: 1.0.0
tags: [graphics, procedural, numpy, animation, ios, swiftui]
platforms: [linux, macos]
---

# Procedural cloud assets

Generating a convincing cloud is mostly about avoiding five specific failure
modes. Each rule below was paid for with a rejected render.

## Ask "what moves per frame" before drawing anything

For an animated asset the performance question is not image quality, it is
which arrays change every frame. Decide the tier first:

| Tier | Per-frame work | Use when |
|---|---|---|
| Static PNG + transform | GPU moves a texture | cloud only needs to drift |
| 3-layer parallax | 3 transforms | depth wanted, cost still ~zero |
| Separate rim channel | 1 LUT + 2 multiplies | the iridescent edge must travel |
| Shape morph | cross-fade 2 fields | cloud must visibly billow |

Keep the rim colour in its OWN channel, never baked into the body pixels.
Baked colour can only be animated by re-rendering the whole cloud; a stored
`rim` (thin-and-sunward mask) plus `heat` (hue index) makes a frame cost one
palette lookup. That mirrors how a fragment shader would do it on device, so
the preview and the shipped version have the same structure.

Use a cyclic palette (first stop == last stop) for any hue that sweeps, or the
loop shows a seam where the ramp wraps.

## Never round-trip float fields through 8-bit images

`Image.fromarray(x*255).filter(GaussianBlur)` quantises to 256 levels. Blur a
height field that way and later `np.gradient` turns every step into a visible
concentric "topographic ring" across the whole render. Keep a float32
separable Gaussian (`np.convolve` along each axis); scipy is often absent.

## Build lobes with MAX, not SUM

Summing metaballs merges them into one smooth envelope — reviewers call the
result "a loaf" or "marshmallow". `np.maximum` preserves each turret's own
shoulder. Then:

- stack lobes at 4 scales (body, turrets, crowns, flank cauliflower);
  single-scale lobes always read as CG blobs
- SUBTRACT a ridged-noise term (`1-|2n-1|`) to carve narrow clefts; smooth
  saddles between lobes are the giveaway of a procedural cloud

Express lobe positions as fractions of the canvas, not pixels, so one layout
rebuilds at any size and a `scale` knob can shrink features for distant layers.

## Opacity from optical depth, not a threshold

`alpha = 1 - exp(-tau)` keeps margins genuinely translucent. A hard threshold
leaves edges opaque to the last pixel, which reads as a cut-out sticker.
Add forward scatter — thin, sun-facing margins should EMIT light — because
that glow is the physical reason backlit cloud edges look luminous.

## One sun, used for everything

Shade with Lambert against a single direction, and ray-march that same
direction to accumulate cast shadows so clefts darken and crowns stay lit.
Index the rim hue by how directly a surface faces that sun (gold at the
hottest point, through pink, to violet at the terminator). A rim whose colours
are keyed to screen X position produces warm patches on both edges, which no
single light source can explain — an immediate tell.

## Verify with numbers, not by eye

Print metrics each render and treat them as gates; vision review is expensive
and slow to iterate against:

- luminance spread of visible pixels >= 40% (under ~30% nothing models)
- crest band mean brighter than base band mean, by a clear margin
- soft-edge fraction (`0.05 < alpha < 0.95`) in 0.10-0.30 — below that the
  silhouette is a cut-out, above it the cloud is fog
- column roughness (`mean|diff(lum,2)|`) well above 0 — near 0 means banding

Add triangular dither before the 8-bit write, or low-contrast gradients
posterise.

Large RGBA PNGs time out in vision review: composite onto a sky colour,
resize to roughly 780px wide and save JPEG before asking for analysis.

## Licensing, if you reach for photos instead

Stock sites' "free" tiers usually forbid redistribution inside an app.
Wikimedia Commons is searchable by licence: prefer CC0 / public domain
(`haswbstatement:P6216=Q19652`, `P275=Q6938433`). Avoid CC BY-SA for a
bundled asset — share-alike can reach the containing work and attribution
must ship in the UI. Photo clouds also resist layered parallax: you cannot
slice a single photo into believable depth.

## Vector cannot do this

SVG `feTurbulence` + `feDisplacementMap` only warps a vector edge, so the
result always reads as a blurred drawn blob. Volume needs a density field,
alpha driven by that field, and lighting from its gradient. Go raster.

## Preview honestly

Render at ~half the target pixel size; cloud art is low-frequency and that is
how it should ship anyway (offscreen texture, upscaled). State plainly that
fps and battery cannot be measured without the real device — a CI simulator
runs on a desktop GPU and its numbers say nothing about a phone.
