---
name: agent-loop-vs-factory
description: "Use when picking a loop, pipeline, or factory harness."
version: 1.0.0
metadata:
  hermes:
    tags: [ralph-loop, orchestration, multi-agent, omniroute, verification]
---

# Loop vs pipeline vs factory vs smart routing

Four things that get conflated. They are **orthogonal**, not alternatives:

| Concern | Mechanism |
|---|---|
| How many times, with what context | **Loop** (Ralph) |
| Verification inside one request | **Pipeline** (critic) |
| Who hands out the work | **Factory** (orchestrator) |
| Which model for this request | **Routing** (complexity combo) |

Pick per concern. Do not treat "we use a loop" as answering the model question.

## Ralph loop (Geoffrey Huntley, Jul 2025)

```bash
while true; do claude < PROMPT.md; done
```

`PROMPT.md` says: read `IMPLEMENTATION_PLAN.md`, pick the single most important task, do it,
commit, exit. The loop restarts with a **fresh context window**.

- **What it actually solves: context rot**, not model selection. Progress lives in files and git
  history, not in the model's memory; each commit is the next iteration's checkpoint.
- **One thing per iteration. Only one.** Huntley's hard rule. Small steps repeated beat one
  giant step that collapses under its own context.
- Philosophy: "deterministically bad in an undeterministic world" — the agent will fail; the
  loop catches it and retries.
- **A bare loop has NO roles and NO per-role models.** One agent, one model, many runs. The
  moment you write roles into `PROMPT.md`, you are building a factory — that IS the factory.
- Fits mechanical work with clear completion criteria (migrations, test coverage, wide refactors).

## Verification gate: machine beats critic

**Prefer machine checks over a critic model whenever they exist**: types, tests, compiler, CI,
browser validation. A critic model can call non-compiling code "looks good"; `tsc` cannot.
Huntley and Pocock both insist the feedback mechanism is types/tests/CI, not another LLM.

Cost argument too: a critic pipeline runs plan → execute → reflect → fix per call and re-runs on
`fail`. Inside a loop of hundreds of iterations you pay that multiplier hundreds of times for a
worse check than `npm test`.

**Use a critic pipeline only where no machine check exists** — prose, architecture decisions,
analysis. There the critic model is the only available reviewer.

## Factory (orchestrator / multi-agent)

Planner splits work and hands slices to specialists. Tools: Composio Agent Orchestrator,
Conductor, Superset — each agent in its **own git worktree** so they don't collide on shared state.

**Only worth it when tasks are genuinely parallel and independent.** Work with blocking edges is
mostly sequential; a loop working the frontier is simpler and does not deadlock on shared state.

## Why complexity routing can't work on chat turns

The needed information **does not exist at routing time**. "Fix the checkout bug" is five words:
could be a missing comma or three days of state untangling. Difficulty lives in the **codebase the
classifier never saw**. No amount of prompt-text analysis recovers it.

OmniRoute's classifier scores syntactic markers (code fences ×5, backticks ×0.5), so
`rename variable x to count` → 1 while a dense distributed-consensus prose question → 3; both
`trivial`. Adding backticks to a trivial request outranks a genuinely hard one.

**In a loop/factory, routing becomes redundant**: complexity was already decided, explicitly and
with full context, when the spec was cut into tickets. Routing guesses what the planner knows.

Still useful for IDE-scale requests where large code context reaches moderate/complex via
`contextSize` — a real signal, not a guess.

## Failover is not escalation

Stock combo behaviour retries the **same prompt** on HTTP error only (429/5xx/timeout), with no
failure context, and nothing checks whether a 200 is correct. Real verification needs the critic
stage or a machine check on the caller's side.

## Do not route the loop through a pipeline combo

Pin a **single strong model** for the loop agent and let tests be the gate. A pipeline combo as the
loop's model stacks two verification layers, multiplies cost per iteration, and makes failures hard
to attribute (bad code vs critic false-`fail`).

Per-role models come from separate one-shot processes (see `multi-model-agents`), because Hermes
has one global model and `delegate_task` cannot pin a model per task.

## Role-based model selection (the working alternative to complexity routing)

Select the model by the **role of the task**, decided by a planner that saw the whole problem —
not by a classifier guessing from prompt text. Roles, strongest to cheapest:

| Role | Tier | Job |
|---|---|---|
| `planner` | strongest + high effort | thinks, never writes final code; splits work into slices |
| `coder` | mid (medium effort) | the implementation |
| `fixer` | cheapest | mechanical edits only |
| `critic` | strong | reads a diff, outputs PASS/FAIL + file:line |
| `loop` | mid | one ticket per iteration in a Ralph loop |

**Effort is part of the model id**, so routing has two axes (model × effort). Raising effort on the
same model is often cheaper than jumping to a pricier one.

**Prefer a cross-vendor critic when quota allows**: a reviewer from a different vendor catches what
a model misses in its own output (blindness to its own patterns). Fall back to same-vendor only when
the other vendor is unavailable.

Implement roles as **separate one-shot processes**, each with a pinned model — Hermes has one global
model and `delegate_task` cannot pin a model per task. See `multi-model-agents` for the runner.

## Verify provider wiring before trusting a config

`/v1/models` is only a **declaration** — some listed models have no working OAuth behind them.
Always confirm with a live request per model, and check quota with a real call rather than reading
config: a vendor can be listed, configured, and entirely dead (HTTP 429 `configured quota threshold`,
or 400 `INVALID_MODEL_ID`). A role table built on an unverified model list fails at the first run.

Resolve the provider slug rather than guessing it; a bare `custom` provider hits the wrong gateway.

## Recommended default

1. Cut the spec into vertical tracer-bullet tickets with blocking edges (`to-tickets`), each sized
   to one fresh context window — this is the loop's input format.
2. Loop one capable model over the frontier of unblocked tickets.
3. Gate on the project's existing test command.
4. Add a factory only when slices are provably parallel.
5. Reserve critic pipelines for unverifiable-by-machine output.
