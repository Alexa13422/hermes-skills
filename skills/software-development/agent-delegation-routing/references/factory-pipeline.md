# Factory pipeline reference

## Role matrix

| Role | Typical tier | Output |
|---|---|---|
| fixer | cheap/fast | narrow edit plus checks |
| coder | balanced | implementation plus tests |
| planner | strongest reasoning | plan, risks, acceptance criteria |
| critic/verifier | independent model line | PASS/FAIL and file:line findings |
| loop | balanced | one bounded ticket per run |

Model names are configuration, not facts. Read the current role map and probe changed IDs before use.

## Live probe recipe

1. Run `agent --list`.
2. For each changed model ID, send a minimal completion through the exact provider and base URL used by the runner.
3. Use the endpoint's accepted syntax; direct cliproxy commonly expects bare IDs, while a router may expect provider-qualified IDs.
4. Confirm a real completion and status, not just `/v1/models` membership.
5. Run one representative role invocation before relying on the pipeline.

## Direct endpoint versus router

| Choice | Preserves | Gives up / risks |
|---|---|---|
| Router | fallback, account rotation, circuit breaking, centralized logs | another routing and auth surface |
| Direct cliproxy | isolation from router overload and explicit model selection | router fallback/rotation/logging; endpoint must be protected with API auth |

Test both keyless and authenticated requests when changing exposure. A production inference endpoint should reject keyless requests.

## Verification handoff

- Planner writes a plan artifact.
- Coder receives the plan and produces the change.
- Critic receives the actual diff and returns `PASS` or `FAIL` with numbered, actionable file:line findings.
- Parent independently checks status, diff, and tests before reporting success.
