---
name: installing-external-agent-skills
description: Install and verify third-party Agent Skills into Hermes.
version: 0.1.0
author: Durer, Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [skills, install, agentskills, verification, uv]
    related_skills: [hermes-agent-skill-authoring]
---

# Installing External Agent Skills into Hermes

For "install this skill" when the user gives a GitHub repo or agentskills.io link.
Covers getting the folder into the right place, installing the runtime it needs,
and proving it actually runs before reporting success. Not for authoring skills
(see `hermes-agent-skill-authoring`) or for `hermes skills install official/...`,
which handles the official catalog itself.

## When to Use

- User pastes a repo/skill URL and says install it
- A skill is present but its scripts have never been executed here
- Don't use for: writing a new skill, or editing one already installed

## Procedure

1. **Read the repo's own install section first** (`web_extract` on the README).
   It names the layout and the runtime. Note the published install command but do
   not run it blindly — step 2.

2. **Copy the folder; do not use the published `npx skills add`.** That installer
   targets the agent dirs it knows (`~/.claude/skills/`, `~/.agents/skills/`),
   and Hermes reads its own active profile instead, so a "successful" install
   lands somewhere Hermes never looks. Clone and copy:
   ```
   terminal: git clone --depth 1 <repo> <scratch>/<name>-src
   terminal: cp -r <scratch>/<name>-src/skills/<name> ~/.hermes/skills/<category>/<name>
   ```
   Published repos often nest the real skill at `skills/<name>/` — copy THAT
   directory (the one holding `SKILL.md`), not the repo root.

3. **Pick the category from what the skill does** and place it under an existing
   `~/.hermes/skills/<category>/`. Keep the upstream skill name unchanged so the
   user's notes and the repo's docs still refer to the same thing.

4. **Confirm Hermes sees it:** `skill_view(name='<category>:<name>')`. This also
   returns `linked_files`, which is the real inventory of scripts and references.

5. **Run the skill's own doctor/health script if it ships one**, then install what
   it reports missing. Treat its output as a checklist, not a verdict — see
   Pitfalls on the interpreter mismatch.

6. **Exercise the real entry points** (next section) before telling the user it
   is installed.

7. **Record it where the user tracks skills** and commit if that store is a git
   repo. Note the source URL, the install path, the verification result, and the
   parts you could NOT verify.

## Verification: run it, don't infer it

A skill is "installed" only when its scripts have produced real output here.
Build a tiny fixture rather than hunting for a sample input — for a
photo/document skill, synthesize one with the metadata and text the skill is
meant to read, then check it round-trips.

Split the entry points into three buckets and report them separately:

- **Offline/local** (lookup tables, parsers, metadata readers) — always verify;
  these must pass or the install is broken.
- **Network** (APIs, Overpass, scrapers, headless browser) — verify at least one;
  a single live call proves the whole transport path.
- **Heavy ML** (model weights downloaded on first use) — state plainly that it is
  unverified and why. Do not run a multi-GB download on a small-RAM host just to
  tick a box; say which code paths that leaves unproven.

Never report a skill as working on the strength of a passing doctor script
alone — doctor checks the environment, not the skill's own code paths.

## Pitfalls

- **A doctor script run with the wrong interpreter lies.** If the skill invokes
  everything through `uv run` (each script declaring its own deps), running
  `python3 scripts/doctor.py` reports libraries missing that `uv run` would have
  installed on demand — and the reverse, passing checks for deps the real
  entry point never sees. Run the doctor the same way the skill runs its scripts.
- **`${CLAUDE_SKILL_DIR}` is substituted only by Claude Code.** Under Hermes,
  `export CLAUDE_SKILL_DIR=<abs path to the skill dir>` first or the skill's own
  documented commands resolve to empty paths. Record this in the user's note:
  it bites every later session, not just the install.
- **Tool-installed binaries land outside the default PATH** (`~/.local/bin` for
  `uv`). Export PATH in the same `terminal` call that uses them; a prior call's
  export does not help a command that re-reads a stale environment.
- **Scripts write their cache and state into the CURRENT directory**, not the
  skill dir. Run them from a scratch dir per task so runs don't collide and the
  skill folder stays clean.
- **A headless browser dependency needs the automation build, not the system
  one.** A present system Chromium does not satisfy a Playwright-based path;
  install the browser the library expects (`uvx playwright install chromium`).
- **Vault/notes stores often forbid new folders.** Read the store's own
  conventions file (e.g. `CLAUDE.md`) before writing, and extend the existing
  catalog note instead of creating a new one.

## Promoting repo-local skills to the global profile

A skill bundle vendored inside another project (`<repo>/.hermes/skills/...`) is
loaded only in sessions whose working directory is that repo, so it is invisible
elsewhere even though it is installed. To promote the generally-useful ones:

1. Inventory the source by description, not by name: `grep '^description:'` across
   every `SKILL.md` under the bundle. Names like `loop-me` or `wayfinder` say
   nothing about scope, and the description is what decides whether it belongs
   globally.
2. Leave behind anything tied to a stack the user does not run (framework-specific
   setup/migration skills), course or exercise scaffolding, and skills that install
   hooks for a *different* agent runtime — those configure Claude Code or similar,
   not Hermes, and will silently do nothing or fight the host.
3. Check every candidate name against the existing global tree *including category
   directory names*, not just skill names. A skill whose name matches an existing
   category (`research/`) collides in lookup; rename it or leave it behind.
4. Strip CRLF after copying:
   `find <dest> -name '*.md' -exec sed -i 's/\r$//' {} +`. A bundle checked out on
   Windows carries `\r` into the frontmatter, and a trailing `\r` on the `name:`
   value makes lookup by name fail while the file still looks correct.
5. Confirm with `skills_list(category='<category>')` and report the count plus the
   exclusions with their one-line reasons.

Tell the user which ones you skipped and why; an unexplained partial copy reads as
a failed install.

## Each agent runtime reads its own directory

The same `SKILL.md` format is read by several runtimes, but each scans only its
own paths: Hermes reads its active profile (`~/.hermes/skills/`, plus
`skills.external_dirs` when configured), Claude Code reads `~/.claude/skills/`
(personal) and `<repo>/.claude/skills/` (project). A vendored bundle at
`<repo>/.agents/skills/` is a convention of whoever shipped it and is read by
**neither** unless something points at it — so "the skills are in the repo" does
not mean any agent can see them. Before concluding a bundle needs copying,
inventory what is already vendored in the current project: it may be the same
bundle, already tracked, just unreadable by the runtime in use.

To expose a vendored bundle to a second runtime, symlink that runtime's expected
directory at it (`ln -sfn ../.agents/skills .claude/skills`) rather than copying.
Two copies of the same tree drift, and the next person to patch a skill has no
way to know which copy is read. Verify by reading a `SKILL.md` *through* the link
before reporting success, and commit the link itself.

When comparing a vendored bundle against another checkout, diff with
`diff -rq --strip-trailing-cr` first — a Windows checkout differs on every file
by line ending alone, which otherwise reads as 38 skills having diverged.

## Privacy gate

Before recording a skill that uploads user content to third-party services
(reverse image search, OCR APIs, cloud vision), say so explicitly in the note
and check it against the destination store's privacy rules. A skill that sends
material to external endpoints must never be pointed at a personal vault's
contents.

## Verification Checklist

- [ ] Folder holding `SKILL.md` copied into the Hermes active profile, not `~/.agents/skills/`
- [ ] `skill_view(name='<category>:<name>')` resolves
- [ ] Runtime the skill declares is installed (`uv`, browser, etc.)
- [ ] At least one offline entry point produced real output on a fixture
- [ ] At least one network entry point returned live data
- [ ] Unverified paths named explicitly, with the reason
- [ ] `CLAUDE_SKILL_DIR` / PATH requirements written into the user's note
- [ ] Note committed if the store is a git repo
