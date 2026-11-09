# Pipelines for one organic, photoreal object

## Choosing the pipeline

| Pipeline | Realism ceiling | Animation it supports | Per-frame cost |
|---|---|---|---|
| Vector / SVG shape | low — always reads as drawn | path morph, transform | ~free |
| SVG `feTurbulence` + `feDisplacementMap` | low — deforms a vector edge, so it yields a blurry drawn blob | animated seed/offset | moderate, CPU filter |
| Raster procedural (numpy/Pillow) baked to PNG | high | transform, scale, crossfade | ~free (one texture) |
| 3–4 baked PNG layers, parallax drift | high, with real depth | layers drift at different speeds; body appears to churn | ~free, N textures in memory |
| Metal/`.colorEffect` fBm shader | highest, never repeats | fully live, time as a parameter | real — scale with the pixel area it covers |

Rules that fall out of the table:

- An "ultra-realistic" request rules out the vector pipelines outright. Volume
  cues — multi-octave density, alpha derived from density, self-shadowing from the
  density gradient — cannot be expressed as a deformed outline.
- One PNG can only float and breathe; it cannot deform, so it reads as a sticker
  sliding around. Depth needs several layers.
- A live shader is justified for the small area where procedural variation is
  actually visible (a shimmering rim, a few percent of the screen) while the body
  stays baked layers. Reserve the expensive effect for where the eye can tell.
- Render a full-screen noise shader into a reduced-size target (roughly 0.4x) and
  upscale — the noise is low-frequency anyway, so the loss is invisible while the
  fill cost drops with the square of the factor.

## Physical rules for raster procedural generation

- **Blend lobes with MAX, not a sum.** Summing metaballs merges every bump into
  one smooth wrapper (a loaf); max preserves each crown's shoulder, and a
  noise-modulated threshold then cuts narrow cliffs between them instead of
  rounded saddles.
- **Use optical depth for alpha: `alpha = 1 - exp(-tau)`.** Thin edges come out
  genuinely semi-transparent. Add forward scatter that *increases* luminance where
  the body is thin — that is the mechanism behind glowing backlit edges, and a
  binary alpha can never produce it.
- **One light vector for everything.** Lambert against a single `SUN`, occlusion
  marched *along the sun ray* rather than straight down, and any iridescent rim hue
  indexed by how much the surface faces the sun (hot point -> warm -> cool).
  Independent choices make the colour sequence contradict the light and the rim
  tears at the ridge.
- **Never round-trip a float height field through an 8-bit image to blur it.**
  PIL-based blurring quantizes the field to 256 levels, and the next gradient turns
  those steps into concentric topographic contour rings across the whole object.
  Where `scipy` is unavailable, write a float32 separable Gaussian — a few lines,
  and it removes the banding completely.
- Break the base/underside with noise instead of a straight horizontal cut, and
  detach a few satellite puffs; a clean baseline is the strongest "generated" tell.

## Metrics worth targeting

- Luminance p5/p95 spread ~40-50% — below ~25% the object looks flat and pasted.
- Soft-edge fraction ~0.12 — near 0.04 the silhouette is a hard cutout; near 0.28
  the whole thing is fog.
- Crown clearly brighter than base (e.g. ~210 vs ~120 on 0-255).

These being in range is necessary, not sufficient. Keep the visual critic in the
loop.
