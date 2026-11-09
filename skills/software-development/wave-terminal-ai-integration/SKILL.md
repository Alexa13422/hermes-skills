---
name: wave-terminal-ai-integration
description: "Use when configuring Wave AI with a custom model gateway."
---

# Wave Terminal AI custom gateways

## Procedure
1. Identify the actual Wave install and version, then consult the current Wave AI documentation before changing configuration. Wave AI modes use `~/.config/waveterm/waveai.json`; on this Windows host that resolves to `C:\Users\andra\.config\waveterm\waveai.json`.
2. Verify the gateway before configuring Wave. For an OpenAI-compatible router, call both `GET /v1/models` and a non-trivial `POST /v1/chat/completions` through the exact Tailscale endpoint, authorization key, and intended router/combo model. A short prompt can fail a router's quality validation; use an answer-length requirement when probing smart-routing combos.
3. Create a custom mode with the **full** chat-completions URL, not merely a base URL. Use `ai:apitype: "openai-chat"`, a router model/combo known to pass the probe, `ai:apitokensecretname`, and only verified capabilities.
4. Set `waveai:defaultmode` in `settings.json` to the mode key, not its display name. Preserve existing JSON settings.
5. Store the API key through Wave's Secrets UI or `wsh secret set` from a Wave-managed terminal. Never put the key in `waveai.json` or claim setup is complete until the secret is stored and an in-Wave request succeeds.
6. If configuring a remote router over Tailscale, target the router's own port and endpoint. Do not silently bypass it to a downstream provider/proxy just because that endpoint happens to respond.

## Windows notes
- Wave's config root is `C:\Users\andra\.config\waveterm` even though the app and runtime state live under AppData.
- `wsh` called from an ordinary external shell may reject secret/config operations because `WAVETERM_JWT` is absent. Use Wave's terminal block or Settings → Secrets in that case.
- Wave logs config reads in `C:\Users\andra\AppData\Local\waveterm\Data\waveapp.log`; use them to confirm a mode file was loaded, but validate actual inference with a request.

## Pitfalls
- Point `ai:endpoint` at `/v1/chat/completions`, not `/v1`; Wave does not append the path and a base URL produces a 404.
- Keep endpoint credentials in Wave Secrets; configuration JSON is readable plaintext and must not contain an API key.
- Distinguish a running router from a working smart combo; `/v1/models` can return 200 while a selected combo rejects requests because of expired upstream auth or its own response-validation policy.
- Do not treat an unauthenticated health endpoint as proof that inference access works; verify the authenticated models and chat endpoints separately.
