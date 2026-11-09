---
name: llm-gateway-tuning
description: "Use when tuning an LLM gateway like OmniRoute."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [llm-gateway, omniroute, routing, quotas, compression, free-tier]
    related_skills: [blocked-page-recovery]
---

# LLM Gateway Tuning (routing / quotas / token economy)

## When to Use

Updating, auditing, optimizing (speed / token economy), or explaining a self-hosted multi-provider LLM gateway dashboard, or recommending free providers to add to it.

Class: user runs a local multi-provider AI gateway and wants it updated, "maximally optimized" (combos, fallback, quotas, compression), explained, or extended with free/subscription providers. Covers OmniRoute (Next.js, `localhost:20128`) and CLIProxyAPI (Go single binary, OpenAI-compatible, good for an always-on Pi/VPS; 9Router is its Next.js reimplementation).

- OmniRoute specifics (npm-global update, vault login, dashboard tables): see `references/omniroute.md`.
- CLIProxyAPI specifics (headless install, systemd, OAuth-over-SSH-tunnel login, fill-first quota fallback): see `references/cliproxyapi.md`.

User style: speaks Ukrainian, informal; wants the agent to *do* the tuning, then a compact report: what changed, what was verified, what's left. For "explain the settings" asks, tables per sidebar section with ⚡ (speed) / 💰 (token economy) / ✅ (already changed) markers worked well.

## Procedure

1. **Identify install + version.** `netstat -ano | grep <port>` → PID; check global npm (`%APPDATA%\npm\node_modules/<pkg>/package.json`) vs `registry.npmjs.org/<pkg>/latest`. Update for npm-global installs on Windows: stop the process first (EBUSY/EPERM otherwise), `npm install -g <pkg>@latest`, restart. Data lives outside the package, so settings survive.
2. **Log in via vault, never ask for the password in chat.** `browser_vault_list` → `browser_vault_save_login` (user types it in masked UI) → click submit. Re-use the handle with `browser_vault_fill` on every re-login.
3. **Snapshot current state through the management API from the logged-in tab** (`browser_console` + `fetch`), redacting any key matching `/key|token|secret|password|cookie|refresh|access/i` before returning. Stash results in `window.__x` and read them in a second call.
4. **Read official docs from raw GitHub** (curl into scratch dir, grep headings) and the installed source for exact schemas (`src/shared/validation/schemas/*.ts`) — docs lag the code.
5. **Back up the DB before any write** (OmniRoute: `PUT /api/db-backups`) and tell the user the backup filename.
6. **Probe every candidate model with a real tiny request before putting it in a combo** (`curl localhost:<port>/v1/chat/completions`, small `max_tokens`, loop over models, print status + first 150 chars). Catalog listings ≠ what the account actually serves: free tiers reject many listed models with 400; some upstreams return an "Available models: [...]" list in the error — use it.
7. **Clear stale lockouts after probing** (`DELETE /api/resilience/model-cooldowns {all:true}`) — failed probes put models into cooldown and the next probe then misreports "all credentials cooling down".
8. **Apply changes** (combos, settings, resilience, compression), re-GET to verify each, then report.

## Recommended defaults (subscription-heavy coding setup)

- Combos by intent, strategy `priority`: a main coding chain, a `code-max` (strongest models first), a `fast` chain (small/flash models for chat/subagents). Order: paid subscriptions first, ToS-risky OAuth providers (flagged `avoid` in the gateway's free-tier catalog) lower, free API-key providers last.
- Enable provider-quota auto-refresh (quota-aware ordering uses stale data otherwise) and set session-affinity TTL (~1h) so agent sessions keep one account and the provider's prompt cache.
- Resilience: honor upstream `Retry-After` hints for OAuth connections too. For speed over persistence, lower combo cooldown wait (default up to 90s) to ~20–30s.
- Compression: `lite` default (safe, ~15%), RTK auto-trigger on large contexts (tool/log output 60–90%). Keep Caveman at `lite` for non-English users (rules are English). Avoid aggressive/ultra/LLMLingua by default — they drop context.
- Keep thinking budget `passthrough` unless the user explicitly trades quality for tokens.
- Don't recommend fusion/chaos/pipeline strategies for economy — they multiply tokens.

Details (OmniRoute endpoints, sidebar map, free-provider shortlist, account quirks): `references/omniroute.md`.

## Restricting what a key advertises (combos-only catalog)

When the user wants the model picker to show ONLY their named combos, do not delete models or
connections — scope the API key. On the `api_keys` row: `catalog_scope='combos'` (what `GET /v1/models`
lists), `allow_auto_combos=0` (hides the ~45 built-in `auto/*` combos, which are combos too and would
otherwise dominate the list), `allowed_models='[]'`, `allowed_combos='["combo/*"]'`. Changes apply to the
next request — no gateway restart.

Verify with the key the client actually uses, not from a bare localhost curl: the gateway rejects
unauthenticated `/v1/models` (`Authentication required`) and a truncated/display key (`sk-2f6...e39e`)
with `Invalid API key`. Read the real secret from the client's env file (`HERMES_CUSTOM_<host>_<port>_API_KEY`
in `~/.hermes/.env` for a Hermes custom provider) and assert the returned id list equals the combo names.

## Pitfalls

- **Use absolute URLs in `browser_console` fetches** (`http://localhost:<port>/api/...`) and check `location.href` first — the controlled tab can reset to `about:blank`, where relative fetches throw "Failed to parse URL". If blank: navigate to `/login`, snapshot, vault_fill, click, then run the whole batch in ONE console call.
- **Take a `browser_snapshot` before `browser_vault_fill`** after navigating — fill can report `supervisor is not active` until the page is snapshotted.
- **Merge, don't replace, nested settings on PUT** (e.g. compression `engines`, `rtkConfig`): GET current, spread, override the few fields; a partial object resets the rest.
- **Don't add "no-auth/free" catalog providers without probing** — many (browser-session or IDE-locked free tiers) fail outside their own client.
- Warn the user explicitly about providers whose ToS forbid third-party proxies (ban risk) rather than silently dropping them.
