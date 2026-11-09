---
name: ai-native-ui-resources
description: Non-slop UI component registries (shadcn-based) for a build.
version: 1.0.0
author: Durer + Hermes Agent
license: MIT
tags: [design, ui, shadcn, components, anti-slop, react, tailwind]
related_skills: [claude-design, popular-web-designs]
---

# AI-Native UI Resources

A curated list of real, current (2026) copy-paste component registries — not template
dumps, not AI-slop galleries. Use this skill to pick the **source material** for a build;
pair it with `claude-design` for the *process/taste* (surface-first composition, anti-slop
self-audit) and `popular-web-designs` when the user wants a known brand's exact look.

## Why this exists

The user explicitly does not want generic "AI design slop" (gradient hero + 3 feature
cards + indigo accent + glassmorphism). These registries are curated by designers who
ship real, intentional animation/interaction — closer to "craft" than "template". Pull
from here instead of inventing components from a stale training-data prior.

## The registries

Most of these are **shadcn-compatible registries** — install via the shadcn CLI, not npm,
so the user gets owned source code, not a dependency.

| Site | What it is | Install pattern |
|---|---|---|
| **ui.shadcn.com** | The base: unstyled, accessible primitives (Radix-based). Foundation everything else builds on. | `npx shadcn@latest add button` |
| **beautifului.dev** | Primitives for AI-native interfaces specifically: streaming text, thinking/reasoning traces, approval cards, tool chips, agent screens. Use for chat/agent UI, not generic marketing. | copy-paste from site |
| **beui.dev** | Animated React/Next.js components (buttons, nav, menus, charts, AI conversation UI). MIT, shadcn-compatible. | `bunx --bun shadcn add @beui/button` |
| **rareui.com** | Small set (~14) of genuinely unusual components: fluid orb, grid reveal, gravity letters, proximity sidebar. Good for one deliberate "signature" moment, not for every card on a page. | `npx shadcn@latest add swamimalode07/rare-ui/{name}` |
| **transitions.dev** | 43+ CSS transitions (not full components) — modals, dropdowns, panels, page transitions. Each snippet is self-contained CSS vars + `prefers-reduced-motion` guard. Use this to fix "AI-generated transitions feel stiff". | copy CSS snippet, or `npx transitions-dev add` |
| **shadcnblocks.com** | Thousands of full-page *blocks* (hero, pricing, dashboard sections) on top of shadcn/ui + Tailwind. Good for structure/layout scaffolding, less for a unique look — restyle after pulling. | shadcn CLI per block |
| **magicui.design** | 50+ animated effects (text effects, animated backgrounds, bento grids, marquees) on shadcn + Framer Motion. Heavier on "wow" effects — use sparingly, one hero effect max per page, not stacked. | shadcn CLI |
| **ui.aceternity.com** | 200+ components: 3D cards, spotlight, aurora backgrounds, timelines, parallax. Same caution as MagicUI — pick ONE signature effect, don't combine three. | shadcn CLI, `ui.aceternity.com/components` |
| **elements.ai-sdk.dev** (Vercel AI Elements) | Official Vercel AI SDK UI kit: conversation threads, message/response components, reasoning panels, tool-call UI. Use this specifically when building a chat/agent product UI, not general marketing pages. | `npx ai-elements@latest add <component>` or shadcn CLI |

## How to pick, by surface (ties into claude-design's surface-first rule)

- **Decide/Learn (landing/marketing)**: shadcnblocks for structure, then restyle colors/type
  yourself (don't ship their default palette as-is — that's how everyone's landing page
  looks the same). Add ONE moment from Aceternity/MagicUI, not several.
- **Agent/chat UI**: elements.ai-sdk.dev first (official, maintained by Vercel), beautifului.dev
  for agent-specific touches (thinking traces, approval cards). Don't reach for generic
  marketing blocks here.
- **Operate/Configure (dashboards, settings, forms)**: ui.shadcn.com primitives + beui.dev for
  motion on state changes (toasts, menu transitions). Skip the flashy 3D/aurora libraries —
  wrong surface for this (see claude-design's "wrong surface" slop tell).
- **Any surface, fixing janky motion**: transitions.dev. This is the single best fix for
  "AI-generated animation feels off" — drop in a real CSS transition instead of inventing one.
- **One deliberate signature flourish**: rareui.com. Use once, not as a pattern repeated
  across the page.

## Anti-slop discipline when pulling from these

1. Never ship a block's default color palette unchanged — recolor to the brand's actual
   tokens (see `claude-design`'s Color section). Default indigo/violet accent is tell #2
   of AI slop.
2. Never stack 2+ "wow" effects (Aceternity + MagicUI + rare UI) on one page. Pick one
   signature moment; everything else should be quiet.
3. Prefer owning the source (shadcn CLI copy) over an npm dependency — matches
   "copy the code, own it" philosophy of every registry above.
4. Run `claude-design`'s Slop Diagnostic (score /10) after assembling the page, before
   calling it done — these registries make it easy to *add* good components but just as
   easy to over-decorate if you don't self-audit the composition.

## Explaining design intent to an AI (how to brief well)

What actually moves output quality, roughly in order of leverage:

1. **Name the surface first** (Monitor/Operate/Compare/Configure/Decide/Explore/Command —
   see `claude-design`). "This is a dashboard" is not enough; say *why* — glanceable state,
   not persuasion — so the model doesn't default to hero+cards.
2. **Send real reference screenshots/links, not adjectives.** "Minimalist" means something
   different to every model run; a screenshot of Linear's settings page or a link to this
   skill's registries pins it down. Point at specific components by name when possible
   ("like rareui's proximity sidebar" beats "a cool sidebar").
3. **Give 2-3 references that agree with each other**, not ten that pull in different
   directions. Conflicting references produce mushy, averaged output — the opposite of
   intentional design.
4. **State what to avoid explicitly**, not just what to include. "No gradient hero, no
   glassmorphism, no generic feature-tile grid" is more useful than "make it look good" —
   this maps directly onto claude-design's anti-slop tells.
5. **Ask for the self-audit back.** Have the agent score its own output against the slop
   diagnostic and report which tells fired, before you review it yourself. Catches most
   issues before you even look.
6. **Iterate on composition before color.** If a draft feels generic, the fix is almost
   always re-layout (surface mismatch, feature-tile grid, center-stack), not a new palette.
   Recoloring a wrong layout never fixes it.
7. **Lock a direction, then stop generating variants.** 3 options max per round; once one
   is picked, consolidate — don't let the project become an endless pile of alternatives.
