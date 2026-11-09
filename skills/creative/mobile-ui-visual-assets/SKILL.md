---
name: mobile-ui-visual-assets
description: Use when making photoreal or animated app UI art.
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [design, assets, procedural, animation, ios, licensing]
    related_skills: [claude-design, ios-photo-app-development, popular-web-designs]
---

# Visual assets for a mobile app UI

## When to Use

Use when a screen's identity rests on one organic, photoreal-looking object (a
cloud, smoke, water, terrain, aurora) that must also move, and sourcing or
generating that object is the task. Covers the source decision, procedural
generation, licensing, and the animation budget. For general page/artifact design
process use `claude-design` instead.

## Support files

- `references/organic-asset-pipelines.md` — pipeline decision table, physical
  rules for procedural generation, target metrics.
- `references/free-asset-licensing.md` — which licences may ship in a closed app,
  and the Commons API queries that filter for them.

## Procedure

1. Ask what the asset must DO before producing pixels. A static PNG and an
   animated object are different deliverables, and a beautiful still is worthless
   if the screen needs the thing to drift and churn. Settle: does it move, what
   moves (whole-body transform, layer parallax, per-pixel procedural), and does it
   loop or run forever.
2. Decide vector vs raster vs photo vs shader against that answer, not against
   convenience — see the decision table in `references/organic-asset-pipelines.md`.
   Rule of thumb: "ultra-realistic" never survives a vector pipeline.
3. If raster-procedural, generate with numpy/Pillow and follow the physical rules
   in `references/organic-asset-pipelines.md` (max-blend lobes, optical-depth
   alpha, one sun, float32 blur). Score every pass with numbers before looking at
   it.
4. If a ready-made photo asset is wanted, source it under a licence that can ship
   inside a closed app — see `references/free-asset-licensing.md`. Read the licence
   field programmatically; never eyeball a gallery.
5. Budget the animation explicitly in terms of what the GPU redraws per frame, and
   say which parts of the cost you could not measure here.
6. Report the verdict plainly, including "this pass is not there yet" with the
   named defects. Do not present a tuned metric as a visual success.

## Always-on rules

- **Numbers before eyes, and a vision model as the critic.** Compute contrast
  (luminance p5/p95 spread), soft-edge fraction, and crown-vs-base luminance for
  each pass; then load the image and accept the verdict. "Cutout, not cumulus",
  "the lobes merged into a loaf", "concentric rings" are real defects even when
  every metric is on target — tuning parameters cannot fix a wrong model.
- **A large RGBA render may time out the vision path.** Composite it over a flat
  background colour and downscale to roughly 800px JPEG first; this also shows the
  asset the way the app will, against the sky/surface it sits on, instead of over
  a transparency checkerboard.
- **Never claim a frame rate or battery figure you did not measure on the target
  device.** A desktop-GPU simulator render says nothing about a phone. Architect
  the headroom (reduced-resolution shader target, capped tick rate) and state
  plainly that only the user can confirm it on hardware.
- **Separate gestures by zone, not by angle.** A vertical swipe owning the whole
  screen and a horizontal swipe living strictly inside one subview is stable; two
  recognizers competing over the same area on direction alone judder on any
  diagonal movement.
- **Glow travels along the silhouette, never behind it.** Stroke the same path
  that fills the shape, or sample the body's own edge. A blurred band placed under
  the shape reads as a rendering defect rather than light.
- **When the user says to look for a ready asset instead of generating one, stop
  generating.** Repeated parameter tuning after that instruction is ignoring a
  correction, not diligence.
- **Read a generator file fully before rewriting it.** A whole-file write over a
  script that was never read lands as a blind patch; start the next pass as a new
  numbered file instead and keep the previous pass intact for comparison.

## Reporting to this user

- No step-by-step narration while generating. One short message per pass at most:
  what the metrics say, what the critic says, what is still wrong.
- Name the open decision at the end as a single question with concrete options
  (procedural layers vs photo layers, shader vs PNG), not an open-ended "what do
  you think".
- State disproven approaches plainly; a failed pass with a named mechanism is
  progress and is received as such.
