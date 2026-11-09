---
name: architecture-documentation
description: "Use when writing per-folder ARCHITECTURE.md docs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [architecture, documentation, onboarding, codebase-map, decision-records]
    related_skills: [api-contract-documentation, codebase-inspection, hermes-agent-skill-authoring]
---

# In-repo architecture documentation

Write `ARCHITECTURE.md` files that make a codebase navigable to the next agent or
developer: what each folder owns, which boundaries must hold, which decisions were
already made and WHY, and which traps cost time.

## When to Use

- "запиши архітектурні рішення в .md", "document the architecture so you can find
  things later", "кожна папка має свій опис"
- Onboarding docs, a decision log, or a map an agent reads before touching code
- Refreshing docs that drifted after a feature landed

**Not for:** an external handoff contract for an integrator (`api-contract-documentation`),
LOC/language statistics (`codebase-inspection`), or authoring skills
(`hermes-agent-skill-authoring`).

## The artifact: one file per significant folder, plus a root index

```
ARCHITECTURE.md                       monorepo shape, data flow, decision table, INDEX, maintenance rules
apps/<app>/ARCHITECTURE.md            that app: layers, config traps, schedules, gates
apps/<app>/src/<area>/ARCHITECTURE.md the area: boundary, invariants, where-to-add
```

Every child file opens with an up-link to its parent and down-links to its children,
so a reader who lands mid-tree can walk out. The root file carries the index table of
all of them — a doc set with no index is a doc set nobody finds.

## Step 1 — Derive from code, never from the existing README

Read the real thing before writing a line: directory listings, config files, module
entry points, cron/job declarations, route trees, the top 30–40 lines of each
non-obvious file (the WHY usually lives in the header comment). Batch these reads —
independent listings and file reads go in ONE turn, not one per round-trip.

Upstream starter READMEs are actively misleading and must not be a source: a repo can
ship an unmodified starter README naming `pnpm` while the project runs `npm` with a
`package-lock.json`. State the real tool and, when the discrepancy is a known trip
hazard, say explicitly that the README is not the reference.

Harvest existing prose before inventing it. Header comments, root `AGENTS.md`, and
agent-instruction files already contain decisions with their rationale — lift and
condense those rather than paraphrasing from a guess. A decision you cannot trace to
code or to an existing note does not go in the file.

## Step 2 — Write boundaries, invariants, decisions, traps

Four things earn space, in this order of value:

1. **Boundary** — what this folder owns and what it must not do. A layer table with a
   can/cannot column is the densest form: `mapper.ts: pure functions | no I/O, no container`.
   Add the one sentence of WHY the boundary exists ("so mappers test without DB or network").
2. **Invariants** — rules that must hold for the system to be correct: the identity key,
   idempotency, "one bad record must not kill the pass", "writes only through workflow X".
3. **Decisions + rationale** — a `| рішення | чому |` table. The rationale is the
   payload; a decision without it gets reverted by the next person who finds it
   inconvenient.
4. **Traps that fail silently** — the highest-value lines in the whole doc. Each is an
   imperative rule plus the mechanism: "changing `PRODUCT_LIST_FIELDS` breaks the volume
   filter — `volumeValues()` needs `*variants.options` for `option.title`, and it degrades
   with no error".

Mark a known limit as a limit, not a bug ("in-memory filtering over the first 100 rows
is the ponytail ceiling; at catalog scale move it to a search index, do not raise the
limit"). Preserve negative decisions too — "X was removed by the owner's decision, do
not restore it" prevents a well-meaning regression.

## Step 3 — What must NOT go in

- **A file listing.** It rots within a week and the tooling already answers it (graphify,
  `search_files`). Name files only when a file IS the decision (`publish-policy.ts`).
- **Duplication of always-loaded context.** If the root `AGENTS.md`/`CLAUDE.md` already
  states a rule, link to it; restating it means two copies that will disagree.
- **History and TODOs.** Changelog belongs in `CHANGELOG.md`, plans in `ROADMAP.md`.
  An `ARCHITECTURE.md` describes the present tense only.
- **Narrative.** No "we tried X and then Y". The rule, the mechanism, done.

Budget 60–150 lines per file. Longer means it is becoming a wiki and will not be read.

## Step 4 — Embed the maintenance contract in the root file

Docs that nobody is told to update are stale docs. The root file ends with a
"how to maintain" section stating:

- **When to update:** in the SAME commit as a change that adds/removes a module, job,
  workflow, route, data-layer file, or folder; moves a responsibility boundary;
  overturns a listed decision; or adds a trap.
- **What to write / what not to** (Step 2 and Step 3 condensed).
- **Format:** line budget, paths absolute from repo root, the documentation language.
- **Pre-commit check:** every mentioned path still exists, no statement contradicts the
  code, cross-links between the files resolve.
- **New folder or module → create its `ARCHITECTURE.md` and add a row to the index.**

## Step 5 — Wire it into the agent-instruction file, and expect a refusal

The doc set only gets read and refreshed if the repo's agent-instruction file
(`CLAUDE.md`, `AGENTS.md`, `.cursorrules`) tells agents to start from the root
`ARCHITECTURE.md` and to update the matching file in the same commit.

**These files are write-protected and a non-interactive write is refused** — the guard
exists because they steer every future session, so they need human consent. Do not
retry it, and do not route around it via terminal, `execute_code`, or a sibling path.
Instead: finish the docs, then report plainly that the instruction-file hook is the one
remaining piece, that the write needs approval, and offer the exact snippet for the user
to paste. An unhooked doc set is a real gap worth naming, not something to paper over.

Same guard class on normal files: `write_file` over an EXISTING file refuses without a
current read in this task. Read first, then write; for small changes patch in place.

## Language and report style

**Match the repo's documentation language, not your default.** A repo whose comments
and existing docs are Ukrainian gets Ukrainian `ARCHITECTURE.md` files; mixed-language
docs read as machine output and lose the reader.

Work silently — no step-by-step commentary while reading the tree. Close with: the
file count and total lines, then per-file the two or three findings that change what a
reader will do (the boundary, the silent trap), as short labeled bullets, no tables.
State honestly anything that did not land and why.
