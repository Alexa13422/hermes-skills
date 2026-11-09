---
name: repo-quality-audit
description: Audit a repo's type, lint, and test gates, then fix.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audit, typecheck, lint, monorepo, refactor, verification]
    related_skills: [requesting-code-review, systematic-debugging, test-driven-development]
---

# Repo Quality Audit

## When to Use

- "перевір повний аудит коду", "audit this repo", "що тут не так", "чи нормально написано"
- An unfamiliar or inherited codebase that must be judged AND cleaned
- Before enabling strict build gates on a project that has been ignoring them

**Not for:** reviewing a diff you just wrote (use `requesting-code-review`),
or chasing one specific bug (use `systematic-debugging`).

## Core rule: measure before you claim

Every number you report comes from a command you actually ran in this session.
Never carry a count forward from an earlier turn after editing files — state
"not re-verified" instead. A stale "0 errors" is worse than no claim, because
the user stops checking.

### A green test suite does not verify inline JS/UI behavior

When the change under audit touches server-rendered pages with inline JS/CSS
embedded as string literals (Python/Go/etc. serving a `<script>` block directly),
the backend/unit test suite never executes that JS. It can report 100% green
while a single JS `SyntaxError` anywhere in a shared script block silently
breaks ALL interactivity on every page using it — no click handler fires, no
drawer opens, nothing updates — and the HTTP status still returns 200 with
nothing in server logs to flag it. Treat a delegated agent's "tests pass,
feature implemented" as unverified for this class of change until you
actually load the changed page(s) in a browser and check for JS exceptions
(`browser_console()`, or a short Playwright script's `page.on("pageerror")`
run via `terminal`) — once per page touched, not just the one you eyeball.

A frequent root cause: natural-language text with an apostrophe (English
"don't", or a non-English equivalent like Ukrainian "ім'я"/"зв'язки") embedded
in a single-quoted JS string literal, especially one nested inside a
Python/other-language triple-quoted string. The apostrophe terminates the JS
string early and the remainder becomes a syntax error that a diff review
easily misses. Prefer the Unicode right single quote (’, U+2019) over an
escaped ASCII apostrophe inside such strings — it needs no escaping in either
language's string syntax and cannot accidentally close the quote.

## Step 1 — Baseline, all gates, before touching anything

Run each gate and record the COUNT, not the impression. Counts make regressions
visible; "looks fine" does not.

```bash
npx tsc --noEmit -p tsconfig.json 2>&1 | grep -cE 'error TS'
npx next lint 2>&1 | grep -cE "Error:"      # errors and warnings counted apart
npm test 2>&1 | grep -E "Tests:|Suites:"
```

In a monorepo run each workspace separately — a clean frontend hides a broken
backend when the root script swallows per-package exit codes.

Group errors by rule/file before fixing; it turns "20 errors" into three real
decisions:

```bash
npx next lint 2>&1 | grep -E "Error:" | sed -E 's/.*Error: //' | sort | uniq -c | sort -rn
npx tsc --noEmit 2>&1 | grep -E '^src' | sed -E 's/\(.*//' | sort | uniq -c | sort -rn
```

## Step 2 — Read the project's own conventions first

Read `CLAUDE.md` / `AGENTS.md` / `CONTRIBUTING.md` before proposing anything.
They usually state the package manager, which commands are forbidden, and which
paths are a critical path needing extra verification. Following them is the
difference between a merged fix and a rejected one.

Grep for an existing helper before inventing one (`src/lib/util/`, `helpers/`).
A repo that already has `medusa-error.ts` wants its next error helper in the
same shape, not a new pattern.

## Step 3 — Fix in dependency order, re-measure after each class

Types first, then lint, then cosmetics: type fixes often delete lint errors,
while the reverse is rarely true.

After each class of fix, re-run that gate. Do not batch ten edits and measure once —
you lose the ability to attribute a new failure.

## Step 4 — Critic gate on the real diff

Hand a reviewer the actual `git diff`, never a prose summary of it — a summary
launders exactly the detail that carries the regression.

```bash
git diff > /tmp/audit.diff
```

Name the critical-path files explicitly in the review request (checkout, auth,
payment, sync) so the reviewer weights them.

A FAIL means fix the code, then re-run the critic on the NEW diff. A verdict
belongs to a diff, not to a task.

## Step 5 — Report honestly

Table of before → after per gate. Separate:
- fixed and verified
- fixed but not re-verified
- found and deliberately left (say why)

If a build fails for an environment reason (service not running, missing
credentials), say so explicitly and do not count it as a code defect — but do
not call the build "passing" either. Report the stage it reached.

## Pitfalls

- **A type-only refactor can change runtime payloads.** Replacing `as any` with a
  typed accessor silently rewrites what reaches the API: `formData.get()` returns
  `string | null`, so coercing absent fields to `""` sends empty strings where the
  old code sent `null` — in a checkout that overwrites saved address fields.
  Preserve the ORIGINAL value shape, including null, and let the type describe it.
- **`catch (e: any) { return e.message }` returns `undefined` for non-Error throws.**
  Narrow `unknown` through a helper that falls back to a readable string; a thrown
  string or `{code}` object otherwise surfaces as an empty toast.
- **Prefer `@ts-expect-error` over `@ts-ignore`.** It fails the build when the
  suppression is no longer needed, which is how you discover suppressions to delete;
  `@ts-ignore` silently outlives its cause.
- **`ignoreBuildErrors` / `ignoreDuringBuilds` are why the errors accumulated.**
  Flag them, and propose turning them off only once the counts are at zero —
  otherwise the next build breaks the user's workflow.
- **Lint autofix does not touch most real rules.** `no-explicit-any`,
  `ban-ts-comment`, `no-unused-vars` and unescaped entities need hand edits;
  running `--fix` and re-measuring an unchanged count is the tell.
- **Check whether the framework's control-flow escapes your try block.** Next.js
  `redirect()` throws by design, so a `catch` around it swallows the navigation.
  Verify redirect calls sit OUTSIDE the try.
- **An unused-args lint rule usually has a configured escape hatch.** Read the
  regex in the message (`/^_/u`) and rename rather than deleting a parameter that
  is part of a public signature.

## Judging "is this written well"

When the user asks for a verdict, answer it directly and separate architecture
from configuration — they have different fixes and different urgency:

- **Architecture:** does it extend the framework or fight it? Are data access and
  UI separated? Do tests cover the non-trivial parts?
- **Configuration/performance:** disabled build gates, disabled image
  optimization, server-only deps in a client bundle, heavy libraries on a
  critical render path.

Give the verdict in one sentence, then the evidence. Do not hedge into a list of
neutral observations — the user asked for a judgment.

Before blaming a heavy dependency for slow loading, confirm HOW it is loaded.
A library pulled at runtime by a plain script or an import map is not affected
by bundler-level code splitting, so `dynamic()` will not defer it.

For such a runtime-injected asset, the working lever is a start CONDITION, not a
bundler hint: gate injection behind `IntersectionObserver` (so an asset below
the fold is never fetched on a phone) plus `requestIdleCallback` (so it does not
compete with first-paint resources). `prefers-reduced-motion` alone only stops
the animation — the bytes still download.

When deferring injection, three details decide whether it works:
- Keep the injected `<script>`/import map GLOBAL and one-shot. Per-mount
  injection with cleanup-on-unmount removes the import map from under a module
  that has not finished loading, breaking its bare-specifier resolution on
  client navigation. Check the asset already guards its own registration
  (`if (!customElements.get(...))`) before assuming re-injection is needed.
- Carry a `cancelled` flag and set it in cleanup: a deferred callback can fire
  after unmount and start a download for a page the user left.
- Cancel with the same API you scheduled with. Mixing `setTimeout` with
  `cancelIdleCallback` is a silent no-op, so record which path was taken instead
  of re-testing feature support at cleanup time.

## Report style

Work silently. Do not narrate steps, commands, or what you are about to do —
progress commentary actively annoys; only findings and the result belong in the
reply, and the result short.
