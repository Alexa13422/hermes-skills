# Ralph loop: concrete setup

## Files

- `PROMPT.md` — constant instruction, re-fed every iteration.
- `IMPLEMENTATION_PLAN.md` — mutable state on disk; the agent updates it and commits.

## PROMPT.md shape

```markdown
Study IMPLEMENTATION_PLAN.md and choose the single most important
unblocked task. Do ONLY that task.

Then:
- run <project test command>
- if it fails, fix it before finishing
- update IMPLEMENTATION_PLAN.md (mark done, note anything discovered)
- commit with a descriptive message
- exit

Do not start a second task.
```

## Harness

```bash
#!/usr/bin/env bash
PROMPT_FILE=${1:-PROMPT.md}
MAX_ITERATIONS=${MAX_ITERATIONS:-0}   # 0 = unbounded
ITERATION=0
[ -f "$PROMPT_FILE" ] || { echo "missing $PROMPT_FILE"; exit 1; }
while true; do
  if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
    echo "reached max iterations: $MAX_ITERATIONS"; break
  fi
  ITERATION=$((ITERATION + 1))
  echo "── iteration $ITERATION ──"
  <agent-cli> -p < "$PROMPT_FILE" || echo "iteration failed, continuing"
done
```

Always set `MAX_ITERATIONS` on the first few runs. An unbounded loop with a broken exit
condition burns quota silently.

## Exit gate

The loop ends when the plan file has no unblocked tasks left. Make the agent state that
explicitly ("PLAN COMPLETE") and grep for it, or check the plan file between iterations —
do not rely on the model deciding to stop on its own.

## Known failure modes

- **No commit per iteration** → next iteration has no memory of the work; progress lost.
  Committing is the persistence mechanism, not an afterthought.
- **More than one task per iteration** → context fills, quality collapses. This is the rule
  that gets broken first.
- **No machine check in the prompt** → the loop happily commits broken code for hours.
- **Plan file never updated** → the agent redoes the same task forever.
