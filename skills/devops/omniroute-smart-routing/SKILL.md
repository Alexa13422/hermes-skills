---
name: omniroute-smart-routing
description: "Configure OmniRoute routing, combos, critic pipelines."
version: 1.0.0
metadata:
  hermes:
    tags: [omniroute, routing, llm-gateway, combos, pipeline]
---

# OmniRoute smart routing & critic pipelines

Local OmniRoute install: `/usr/lib/node_modules/omniroute` (source readable as `.ts` under `src/` and `open-sse/`).
State DB: `~/.omniroute/storage.sqlite`. Logs: `~/.omniroute/logs/application/app.log` (JSON lines).
Pi instance: `http://100.96.33.8:20128`, dashboard login in Hermes vault (`requireLogin: true`).

## Access

Management API (`/api/*`) requires a **dashboard session cookie** — the `/v1` API key returns 401.
Workflow: `browser_navigate` to `/login` → `browser_vault_fill` → click Continue → then run
`fetch(..., {credentials:'include'})` via `browser_console(expression=...)`. That is the only way to
reach `/api/settings/*` and `/api/combos` without hand-editing SQLite.

## Hard-won API quirks

- `/api/settings/combo-defaults` accepts **PATCH only**. PUT → 405, POST → 405.
- That PATCH **replaces the whole `comboDefaults` object**, it does not merge. GET it first, spread, then send back — otherwise every default is wiped.
- Migration `103_strip_legacy_combo_config_keys.sql` strips `complexityAwareRouting` (and `manifestRouting`, `maxComboDepth`, `shadowRouting`, `evalRouting`, …) from `combos.data` on save. Put these in **global `comboDefaults`**, never in a per-combo config — a per-combo value is silently deleted.
- Config cascade: `DEFAULT_COMBO_CONFIG → settings.comboDefaults → settings.providerOverrides[provider] → combo.config`.
- `DEAD_COMBO_CONFIG_KEYS` (truly dead): `pipelineConcurrency`, `resetAwareEnabled`, `resetAwareWindow`. The others listed in migration 103 ARE still read at runtime.

## Complexity-aware routing

Only `strategy: "auto"` combos run the scoring engine that reads the classifier
(`open-sse/services/combo/resolveAutoStrategy.ts`, gated by `config.complexityAwareRouting`).
Priority / reset-aware / round-robin / cost-optimized are traffic distribution only — blind to request content.

Enable (global defaults, full object):

```js
// in browser_console on the dashboard origin
const cur = (await (await fetch('/api/settings/combo-defaults',{credentials:'include'})).json()).comboDefaults;
await fetch('/api/settings/combo-defaults',{method:'PATCH',credentials:'include',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({comboDefaults:{...cur, complexityAwareRouting:true,
    scoringWeights:{quota:0.12,health:0.15,costInv:0.10,latencyInv:0.08,taskFit:0.15,
      stability:0.05,tierPriority:0.05,tierAffinity:0.15,specificityMatch:0.20,
      contextAffinity:0.03,sessionAvailability:0.02,resetWindowAffinity:0,connectionDensity:0}}})});
```

Default `specificityMatch`/`tierAffinity` are 0.0476 each → complexity affects ranking ~9%, drowned by
health/quota. Raise both or the flag changes nothing observable. Weights are normalized to sum 1.

### The classifier's real limitation

`open-sse/services/specificityRules.ts` scores **syntactic markers**, not semantics:
code-fence count ×5, inline backticks ×0.5, regex hits (`function\s+\w+\(`, `import ... from`) ×2,
`contextSize` 0 points under 1000 tokens, reasoning keywords (`therefore`, `step by step`).
Thresholds in `specificityDetector.ts:60`: trivial ≤5, simple ≤20, moderate ≤40, complex ≤65, expert >65.

Verified: `rename variable x to count` → score 1; a dense distributed-consensus/proof/refactor prompt
→ score 3. Both `trivial`. Short prose never escapes `trivial`; adding backticks to a trivial request
scores *higher* than a hard prose request.

Do NOT "fix" this by lowering the thresholds — that amplifies noise (a stray backtick then outranks a
hard task). The only useful patch adds signal, e.g. a domain-keyword list in `detectDomainSpecificity`
(`prove|invariant|linearizab|consensus|byzantine|race condition|refactor|deadlock|distributed`). Any
such edit is a file patch that `npm update omniroute` will revert.

Practical consequence: complexity routing is useful for IDE-scale requests (large code context reaches
moderate/complex via `contextSize`), near-useless for short chat turns.

## Critic pipeline (ROUTE → EXECUTE → VERIFY → ESCALATE)

`auto` and pipeline are **compatible, not exclusive** (`targetResolution.ts:395`: `strategy === "auto"`
+ `config.pipeline_enabled` → `dispatchSmartPipeline`). That combination gives complexity scoring AND a critic.

Stages are hardcoded per task type in `src/domain/pipeline.ts` (`TASK_STAGES`), chosen by intent
classification, not by score:

- `code`: plan(best-reasoning) → execute(cheapest) → reflect(moderate) → fix(cheapest)
- `math`/`reasoning`: execute(best-reasoning) → reflect(moderate)
- `creative`: execute(moderate) → reflect(best-reasoning)
- `medium`: execute(moderate); `simple`: execute(cheapest)

Fitness tiers (`pipelineRouter.ts`): `best-reasoning` minFitness 0.85, `moderate` 0.6–0.9, `cheapest` maxFitness 0.75.
Tiers resolve against the combo's own model list via `getTaskFitness`, so a pipeline combo needs models
spanning several fitness levels or every stage collapses onto the same model.

Critic contract (`src/domain/prompts.ts`) — strict JSON, unparseable output counts as `fail`:
`{"status":"pass","confirmation":"…"}` or `{"status":"fail","issues":[…],"corrected":"…"}`.
On `pass` the `fix` stage is skipped. On `fail` the whole pipeline re-runs up to `max_reflection_loops`.

Key config: `pipeline_enabled: true`, `max_reflection_loops: 2`,
`skip_pipeline_for_tokens_under: 50` (short prompts bypass the pipeline — keeps cost sane).

## Failover vs escalation — do not conflate

Stock behaviour is **failover**, not escalation: the next target is tried only on HTTP error (429/5xx/timeout)
or when `responseValidation` rejects a 200. The retry sends the *same* prompt with no failure context, and
nothing checks whether a 200 is actually *correct*. Real verification requires the pipeline critic, or a
machine check (compiler/tests/schema) on the caller's side.

`responseValidation` (`open-sse/services/combo/responseValidation.ts`) is substring-only (no regex, no ReDoS):
`forbiddenSubstrings`, `requiredSubstrings`, `minContentLength`, `jsonPathPredicates`. Useful for refusal
text (`I cannot help`, `as an AI`) and truncation (`minContentLength`), nothing deeper.

## Cross-vendor quota failover

Failover only works **inside one combo** — two sibling combos never fall through to each other.
To keep prompt caching per vendor while still failing over on quota exhaustion, nest them:

```js
// per-vendor smart combos, then a priority parent
{name:"main-smart", strategy:"priority",
 models:[{kind:"combo-ref", comboName:"claude-smart"},
         {kind:"combo-ref", comboName:"codex-smart", fallbackOnlyOnQuotaExhaustion:true}],
 config:{nestedComboMode:"execute", maxComboDepth:3}}
```

`fallbackOnlyOnQuotaExhaustion: true` on a combo-ref **requires** `nestedComboMode: "execute"`, else the
zod refinement returns 400 (`requiresQuotaOnlyComboRefExecute`).
Mixing vendors inside one combo breaks prompt caching on every hop — that is the reason to nest per vendor.

## Verification

Always confirm with a live request and the log, never from config alone:

```bash
curl -sS -X POST http://100.96.33.8:20128/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"code-pipeline","messages":[{"role":"user","content":"…"}]}'
grep -aE "PIPELINE|Complexity-aware" ~/.omniroute/logs/application/app.log | tail
```

Expected lines: `Complexity-aware routing: level=… score=… minTier=… tools=…` and, for pipelines,
one `Stage: tier=… model=…` per stage. A missing `fix` stage means the critic passed.
`routing_decisions` in storage.sqlite has `factors_json`/`score`/`success`/`cost` columns for threshold
tuning, but stayed empty in practice — do not rely on it.

## Route everything through Omni, never cliproxy directly

The Pi runs two stacked layers: OmniRoute `:20128` in front of cliproxy `:8317`. Point every client
(parent agent, `delegation.*`, the `agent` role runner) at `:20128`. Calling `:8317` directly loses
`call_logs` accounting, account rotation on quota exhaustion, and the circuit breaker — and a client
pinned there is invisible in the journal, so its spend cannot be attributed.

`localhost:20128` and `100.96.33.8:20128` are the SAME OmniRoute instance and accept the SAME key;
they are not two services. One key env var can be reused for both provider entries.

### Vendor prefix depends on the layer — this is the #1 false alarm

- Omni `:20128` **requires** the vendor prefix: `claude/claude-opus-5-5`, `codex/gpt-6-sol`.
  A bare id there returns 400.
- cliproxy `:8317` accepts **only** the bare id: `claude-opus-5-5`, `gpt-6-sol`.
  A prefixed id there returns `unknown provider for model`.

Before declaring a model id dead, confirm which port the caller actually uses. Testing a config's ids
against the wrong layer produces a full sweep of `unknown provider` errors on a perfectly healthy setup.

### Hermes delegation config

`delegation.provider` must be the provider **slug** (`custom:omni-pi`), resolved from the base_url via
`find_custom_provider_identity`; bare `custom` is rejected. Agents cannot edit `~/.hermes/config.yaml`
(write tool refuses it as security-sensitive) — use `hermes config set delegation.provider …`. That CLI
sets scalars only, so nested `fallback_providers` lists need the user to hand-edit.

Verify delegation by the gateway log, not the child's self-report: a child claiming its own model name
proves nothing. Dispatch a trivial probe, then check fresh `call_logs` rows carry the child's model next
to the parent's.

```bash
python3 -c "import sqlite3;c=sqlite3.connect('$HOME/.omniroute/storage.sqlite');
print(*c.execute('SELECT timestamp,combo_name,requested_model,model,status FROM call_logs ORDER BY rowid DESC LIMIT 6'),sep=chr(10))"
```

## Security: :20128 answers without a key

OmniRoute `:20128` binds `0.0.0.0` and serves `/v1/chat/completions` **unauthenticated** — a keyless
POST from the LAN returns 200 and burns real quota on the frontier model. cliproxy `:8317` correctly
returns 401. So "bypassing Omni" is not the security risk; Omni itself is the open door. Check with a
keyless POST to the LAN IP before assuming the gateway is protected.

## Models & vendor prefixes

Effort is part of the model id, so routing has two axes (model × effort):
`claude/claude-opus-5-{low,medium,high,xhigh}`, `codex/gpt-5.6-{sol,terra,luna}-{low…ultra}`,
`kiro/claude-sonnet-5-{low…xhigh}`. Prefixes: `cc/`=`claude/`, `cx/`=`codex/`, `kr/`=`kiro/`.
`no-think/` disables thinking. Often cheaper to raise effort on the same model than to jump to a pricier one.

## Verified combo set on the Pi

- `claude-smart` — `auto`, haiku-4.5 → sonnet-5-medium → opus-5-high
- `codex-smart` — `auto`, luna-low → terra-medium → sol-high
- `main-smart` — `priority` parent, combo-refs to both, Codex quota-only
- `code-pipeline` — `auto` + `pipeline_enabled`, 4 models across fitness tiers
