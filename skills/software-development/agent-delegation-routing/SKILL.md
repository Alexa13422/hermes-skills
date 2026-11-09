---
name: agent-delegation-routing
description: Use when routing work across agents or models.
---

# Agent delegation and model routing

Use this skill when a task needs multiple agents, different model strengths, an independent verifier, or a choice between Hermes delegation and a factory runner.

## Procedure

1. Classify the work: `fixer` for narrow mechanical edits; `coder` for implementation plus tests; `planner` for architecture and decomposition; `critic` for independent diff review; `loop` for one bounded ticket.
2. Use `delegate_task` only when one shared delegation model is acceptable. Use the role-based factory runner (`~/.local/bin/agent`) when roles need different models or an independent verifier.
3. For feature work, use `planner → coder → critic`; pass plans and diffs as files.
4. Verify the runner with `agent --list`, inspect its role map, and send a short live probe to each new or changed model ID. A model catalog is not proof that completions work.
5. Default every layer — parent model, `delegate_task` subagents, and the factory runner — to the router, so all spend lands in one accounting log and inherits quota rotation. Reach past it to a direct upstream only on an explicit, stated reason.
6. When parallel agents share a repository, assign exclusive file ownership (including CI/config files), then have the parent integrate one tree; overlapping ownership creates competing artifacts that can conceal an untested path. Never split a module's implementation and its tests across two parallel children: when the mismatch between them later disappears, you cannot tell whether the code was fixed or the test was bent to match the bug. Give one child both, or have the parent diff the test's expectations against the contract itself.
7. Re-run every child's verification command yourself, from the correct working directory, before believing either a pass or a failure. Children report verification they did not actually perform, and a "blocked" claim (missing binary, wrong compiler version) is usually a wrong-cwd artifact — monorepo workspace scripts must run from the repo root, where the declared dev dependencies resolve.
8. Give the verifier the actual diff and require `PASS` or `FAIL`, numbered findings, and file:line references.
9. Pre-flight an external agent CLI before routing work to it — check its auth/health subcommand (for example `claude auth status --text`) and fall back to `delegate_task` when the login has expired, rather than discovering it mid-task.
10. Independently inspect the integrated artifact, status, tests, and actual provider/model before reporting success. If a platform-specific build cannot run locally, commit and trigger the real remote runner before calling it verified; static inspection is not a substitute.
11. When asked whether difficulty-based routing works, inspect the active combo's `strategy` first: `auto` may classify complexity, whereas `reset-aware` and `priority` do not, even if unused auto combos exist. Join the router's actual call metadata (`call_logs`: combo, requested/actual model, status, tokens, timestamp, session tag) with Hermes delegation goals and child model usage; do not mistake a batch's concurrent children for a verified task-to-model join. Keep a local, periodically refreshed task/model audit without prompt bodies, responses, or credentials. A call log proves which model ran, not that its difficulty assignment was appropriate: compare independently judged task difficulty with live classifier decisions before claiming quality. Check the exporter, latest row, and timer state before reporting that logging works.
12. Before publishing a reusable agent workflow to a knowledge vault, separate a verified, reusable procedure from a dated inventory of model pins and gateways. Link to the source skill and repo, record a checked-at date for mutable routing, and omit credentials, request bodies, and personal session history; otherwise future agents treat stale configuration as instructions.
12. When delegating repository reconnaissance for a shared knowledge base, partition by source repo and assign read-only findings first. Have the parent reconcile contradictory copies and write one linked index rather than letting agents concurrently rewrite the vault; this preserves source provenance and avoids cross-repo assumptions.

## Always-on rules

- Keep planning, implementation, and verification separate when correctness matters.
- Route by complexity, not habit; prefer a different model line or vendor for verification.
- Do not replace role-based factory routing with a single global delegation model.
- Prefer the simplest wiring that keeps accounting intact: one router layer for all callers beats per-caller endpoints, because a bypassed child's token spend appears in no log.
- Direct routing can lose router fallback, account rotation, circuit breaking, and centralized logs; protect the direct endpoint with API auth.
- Test authentication on every exposed inference endpoint; production keyless requests must be rejected. Audit each endpoint's auth before calling either the direct or the routed path "the safer one" — the bypass is sometimes the only key-protected port, which is still not a reason to keep it.
- Use the runner's documented one-shot flag (`-z` in the known runner), not a similarly named quiet/help flag.
- Before a multi-step or open-ended request, size it with the ambition ladder (outcome / depth / outside judge) and decide what the parent keeps versus what goes to a role agent — then act. Do not narrate the sizing as a deliverable.
- Pass the machine-readable contract (OpenAPI/schema file) by absolute path to every child that implements against it, and tell each child which sibling files it must not touch. A child told only the prose intent invents its own field names.
- Tell children the project's always-on conventions explicitly (comment language, test-file naming, which dev servers are already running). Children do not inherit the parent's loaded context or the user's repo conventions, and a child that starts a second dev server collides with the user's running one.
- Report wiring as found, not as designed: when asked why a layer is configured some way, check whether it was ever a decision before explaining its benefits. Leftover test wiring reads identically to intent, and inventing a rationale for it ends in a retraction.

## Changing a Hermes delegation pin

Hermes `config.yaml` is security-sensitive and agent file-edit tools refuse to write it. Use the CLI, and read the value back:

```bash
hermes config set delegation.provider <provider-slug>
hermes config set delegation.model <id-in-that-layer's-syntax>
hermes config get delegation.provider
```

`hermes config set` handles scalars only — it cannot write nested lists such as `delegation.fallback_providers`; leave those for the user instead of hand-editing the protected file. A provider whose `key_env` has no matching `.env` entry fails at call time, not at config time, so confirm the env var exists first and back up `config.yaml` and `.env` before switching. Finish by dispatching one throwaway subagent and checking the router's call log — config alone proves nothing.

## Lessons

### Verify a child's verification, never its claim

A child's "tests blocked" or "tests pass" is a self-report about a command run
in ITS cwd. Re-run the suite yourself before believing either direction.
Observed: a child reported `cross-env: not found` and `tsc@2.0.4` as hard
blockers, so a working deliverable came back marked unverifiable; the same
suite ran clean from the monorepo root. Put the exact verification command WITH
its working directory in the task context (`cd <repo root> && npm run test:unit
--workspace=<pkg>`), because a child that cd's into the package picks up the
wrong binaries.

### Parallel children cannot see each other's files

Splitting one module across parallel children makes each re-declare the shared
types it needs, and contract fields present in the schema layer get silently
dropped by the layer that never read it. Either hand one child the shared type
file first and the rest afterwards, or diff every layer against the contract
yourself when they land. Green tests prove nothing here — each child tests only
its own half-view.

### A parallel fan-out leaves no entrypoint

Children each build their assigned layer and none builds the caller that wires
them, so the feature is unreachable while every unit test passes. Grep for a
reference to the new module outside its own directory and tests before
reporting the work as done.

### Mine the child's own caveats before reviewing its code

A structured result field for self-reported gaps (`missing_from_other_layers`,
"not handled", "could not verify") is the highest-yield part of the report:
children name real architectural defects there that their own green tests
cannot fail on. Require such a field in the child's output schema, read it
first, and fix what it names yourself — a child that says "the paginator
accepts no restored cursor, so I replay from the start" has just described a
broken resume path, not a design note. Treat a frank "not handled" as the
correct outcome and keep it in the user-facing summary rather than letting a
sibling's confident prose bury it.

### Hand children product decisions as numbered rules, not intent

When the user has settled behaviour questions, paste those decisions into the
child's context numbered and verbatim, and flag any that reverse an obvious
default ("the owner deliberately rejected unpublishing here"). A child given
only the goal re-derives the conventional answer and silently overrides the
user's choice, which green tests then lock in. Ask the user the open behaviour
questions BEFORE dispatching: a fan-out built on a guessed policy has to be
redone, not patched.

## References

- See `references/factory-pipeline.md` for the role matrix, probe recipe, and direct-vs-router decision table.
- See `references/model-id-probing.md` for layer-specific model ID syntax and the wrong-layer probe pitfall.
