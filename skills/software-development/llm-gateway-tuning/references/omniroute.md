# OmniRoute reference (v3.8.x)

Repo: github.com/diegosouzapw/OmniRoute — docs under `docs/` (raw: `raw.githubusercontent.com/diegosouzapw/OmniRoute/main/docs/<path>`). Useful: `reference/API_REFERENCE.md`, `routing/AUTO-COMBO.md`, `architecture/RESILIENCE_GUIDE.md`, `compression/COMPRESSION_GUIDE.md`, `reference/FREE_TIERS.md`, `guides/FREE_PROVIDER_RANKINGS.md`.
Installed source (npm global, Windows): `%APPDATA%/npm/node_modules/omniroute/` — sidebar map `src/shared/constants/sidebarVisibility/sections.ts`, combo schema `src/shared/validation/schemas/combo.ts`, settings schema `src/shared/validation/settingsSchemas.ts`, strategies `open-sse/services/combo/`.

## Management API (session cookie from dashboard tab)

| Purpose | Call |
|---|---|
| Connections | `GET /api/providers` |
| Combos | `GET/POST /api/combos`, `PUT /api/combos/{id}` (body: `strategy`, `models:[{kind:'model',model:'prov/model',providerId,weight}]`, `config`) |
| Global settings | `GET/PATCH /api/settings` (`autoRefreshProviderQuota`, `autoRefreshProviderQuotaInterval`, `sessionAffinityTtlMs`, `promptCacheAffinityEnabled`) |
| Resilience | `GET/PATCH /api/resilience` (`connectionCooldown.{oauth,apikey}.useUpstreamRetryHints`, `comboCooldownWait.maxWaitMs`, `providerBreaker`) |
| Lockouts | `DELETE /api/resilience/model-cooldowns` `{all:true}` |
| Compression | `GET/PUT /api/settings/compression` (`defaultMode`, `autoTriggerMode`, `autoTriggerTokens`, `engines.*`, `rtkConfig`) |
| Thinking budget | `GET/PUT /api/settings/thinking-budget` |
| Backup | `PUT /api/db-backups` create, `GET` list, `POST` restore |
| Health | `GET /api/monitoring/health` |
| Catalog | `GET /api/models/catalog` |
| Free tiers | `GET /api/free-tier/summary` (`perModel[]`: `poolKey`, `monthlyTokens`, `freeType`, `tos`) |

Inference: `POST /v1/chat/completions` from curl on localhost works without a key (local mode). Model ids `provider/model` (aliases `cx/`, `cc/`, `gh/`, `kr/`), combo names, `auto/coding`, `auto/fast`.

Strategies: `priority` (fallback chain), `reset-aware` (account whose quota resets soonest — useful with several same-provider accounts), `cache-optimized`, `headroom`, `auto`. `fusion`/`pipeline` multiply tokens.

## Sidebar map (speed/economy relevance)

- **OmniProxy**: Endpoints; API Keys (per-tool keys, $ limits, compression toggle); Providers (priority, maxConcurrent); Combos; Combo Studio; Provider Quota ("Edit cutoffs" — skip account at ~10% left to avoid mid-task 429); Quota Sharing; Compression Context group (Settings, Engine Combos, Caveman, RTK, Headroom, Session Dedup, CCR, LLMLingua, Lite, Aggressive, Ultra, OmniGlyph, Studio, Exclusions); Tools; Integrations; Proxy.
- **Analytics**: Usage, Combo Health (failing targets), Utilization, Cache (thrash ⇒ enable session affinity), Compression, Provider Stats (p50/p95 → order the fast combo).
- **Costs**: Costs/Pricing/Budget, Free Tiers, Free Provider Rankings, Radar.
- **Monitoring**: Activity, Logs, Health, Runtime, Resilience/Connections.
- **Configuration**: General, AI (thinking budget; global system prompt adds tokens to every request), Routing, Resilience, Advanced (debug off), Security, Access Tokens, Feature Flags, Cache (semantic cache — repeated prompts only), Sidebar.

## Free providers worth adding (API key, recurring)

Mistral (~1B tok/mo, Devstral/Codestral), Cerebras (fast, ~30M), Groq (fast, ~15M), Gemini AI Studio key (~60M, separate pool from Antigravity), Ollama Cloud (~20M), Z.AI glm-cn (uncapped Flash + signup bonus, ToS ok), OpenRouter `:free` ($10 deposit lifts 50→1000 req/day); tail: Cloudflare Workers AI, SambaNova, NVIDIA NIM. Numbers drift — re-check `/api/free-tier/summary`.

Catalog ToS `avoid`: `agy` (Antigravity), `kiro`, `opencode`, web-cookie providers — ban risk; place low and warn.

## Editing an OmniRoute install with no dashboard reachable (headless Pi/VPS)

The server may run as a plain `node /usr/bin/omniroute` child (no systemd unit — `systemctl status omniroute`
reports "could not be found" even though `netstat -tlnp` shows it listening), so there is nothing to
restart and nothing to read config from except the DB. State lives in `~/.omniroute/storage.sqlite`
(`combos.data` JSON, `api_keys`, `key_value`); back it up to `~/.omniroute/db_backups/` before writing.

The box typically has no `sqlite3` binary — drive the DB with `python3 -c` over SSH instead of installing
anything. Column names in the DB are snake_case while the bundled JS reads camelCase aliases
(`allow_auto_combos ?? allowAutoCombos`); grep the minified `dist/` for the camelCase name to find which
flag a UI toggle writes.

## Account-served model quirks (re-probe; these change)

- Copilot Free accepts only a subset; a rejected model's error lists `Available models: [...]`. gpt-4.1 / gpt-4o / gpt-4o-mini / gpt-5.4-nano served; claude-sonnet-5 and most gpt-5.x did not.
- Kiro Free: claude-sonnet-4.5, claude-haiku-4.5, glm-5 served; claude-sonnet-5 / gpt-5.6-* rejected as invalid model.
- OpenCode free models are locked to the OpenCode client (403). Cloudflare Playground provider requires Playwright's headless Chromium (`npx playwright install chromium-headless-shell`).
