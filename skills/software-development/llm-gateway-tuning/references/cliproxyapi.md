# CLIProxyAPI (Go gateway, self-hosted / headless)

CLIProxyAPI (`github.com/router-for-me/CLIProxyAPI`) is the Go original that 9Router
(Next.js) is a reimplementation of — same class as OmniRoute, but a single static
binary, ideal for an always-on box (Raspberry Pi, VPS). Exposes an OpenAI-compatible
API (`/v1/models`, `/v1/chat/completions`) plus a web management panel, and proxies
provider *subscription* logins (Claude, Codex/ChatGPT, Gemini/Antigravity, xAI, Kimi)
via OAuth — no API keys needed for those.

## Install (Linux/ARM headless)

1. Get arch: `uname -m` (Pi 5 / CM4 = `aarch64`). Grab the matching release asset
   `CLIProxyAPI_<ver>_linux_aarch64.tar.gz` from the GitHub releases — do NOT compile
   Go on the Pi (slow, and Go is usually not installed). `curl -fL -o cliproxy.tar.gz <url>`.
2. Unpack to a dir: `mkdir -p ~/cliproxy && tar -xzf cliproxy.tar.gz -C ~/cliproxy`.
   Contents: `cli-proxy-api` binary + `config.example.yaml`.
3. Write `config.yaml` (see config below). Generate secrets on-box:
   `openssl rand -hex 16` (client api-key), `openssl rand -hex 24` (management secret-key).

## config.yaml — minimum working set (config-version 8)

```yaml
config-version: 8
server:
  host: ""          # empty = listen on all interfaces (LAN + Tailscale)
  port: 8317
  tls: { enable: false }
management:
  allow-remote: true
  secret-key: "<openssl rand -hex 24>"
  disable-control-panel: false
access:
  api-keys:
    - "<openssl rand -hex 16>"   # clients send this as Bearer token
routing:
  strategy: "round-robin"        # or fill-first (see Routing)
oauth:
  auth-dir: "~/.cli-proxy-api"   # where per-provider credential JSONs are saved
```

PITFALL: the binary defaults to `./config.yaml` relative to CWD, and login subcommands
read it too — always pass `--config ~/cliproxy/config.yaml` or run from the install dir,
or it dies with `failed to read config file: open ~/config.yaml: no such file`.

PITFALL: a BARE subcommand like `cli-proxy-api codex` (no leading `--`) is parsed as
"start the server", not "log in" — it tries to bind the port and, when systemd already
runs the service, dies with `bind: address already in use`. Login is always the
double-dash flag (`--codex-login`), and you never need to stop the systemd service to
log in: login writes a JSON into `auth-dir` and the running service's file watcher picks
it up live (log shows `N clients (N auth entries)` climbing).

## systemd autostart (24/7)

Write `/etc/systemd/system/cliproxy.service`: `Type=simple`, `User=<user>`,
`WorkingDirectory=<install dir>`, `ExecStart=<dir>/cli-proxy-api --config <dir>/config.yaml`,
`Restart=on-failure`, `After=network-online.target` / `Wants=network-online.target`,
`WantedBy=multi-user.target`. Then `systemctl daemon-reload && systemctl enable --now cliproxy`.
Verify: `systemctl is-active cliproxy`, `ss -tlnp | grep 8317`, and
`curl -s http://127.0.0.1:8317/v1/models -H 'Authorization: Bearer <api-key>'`
(returns `{"data":[],...}` until a provider is logged in, full model list after).

## Provider OAuth login on a HEADLESS box — the key technique

Login subcommands: `--claude-login`, `--codex-login` (also `--codex-device-login`),
`--antigravity-login` (Gemini), `--xai-login` (Grok), `--kimi-login`. Run with
`--no-browser` so it prints the URL instead of trying to open a browser on the server.

Each login spins an OAuth callback listener on `127.0.0.1:<port>` ON THE SERVER
(Claude → 54545, Codex → 1455; ports differ per provider and per run — READ them from
the command output, don't hardcode). The redirect_uri is `http://localhost:<port>/...`,
so the browser's post-consent redirect must reach the SERVER's localhost. On a headless
Pi that only works through an SSH local-forward of that exact port:

1. Start `cli-proxy-api --<provider>-login --config <cfg> --no-browser`; read the
   printed auth URL and callback port.
2. From the machine that has the browser, open a forward:
   `ssh -L <port>:127.0.0.1:<port> -N <user>@<pi>`  (one tunnel per provider port).
   Verify locally the port LISTENs before handing the user the URL.
3. User opens the auth URL in their browser, consents; redirect to `localhost:<port>`
   travels the tunnel to the Pi and the login completes, saving
   `~/.cli-proxy-api/<provider>-<id>.json`. Confirm via `/v1/models` showing that
   provider's models. Tear the tunnel down after — credentials persist on disk.

Note: CLIProxyAPI prints its own suggested `ssh -L ... root@<public-ip> -p 22` line, but
forward to the reachable admin host/user you actually use (LAN IP, your login), not the
literal root@public-ip it guesses.

Access caveats:
- Codex/ChatGPT via subscription needs a Plus/Pro/Team plan; free ChatGPT logs in but
  requests may be refused (no Codex/API quota).
- xAI/Grok OAuth generally needs paid xAI (or an API key); there is no reliable free-tier
  Grok through this OAuth — try it last and expect it may not grant free access.

## Routing / priority & quota fallback (answering "use provider until its limit, then next")

Providers do NOT expose "time/quota remaining", so NO gateway (this or OmniRoute) can route
on "1 hour of quota left". What they CAN do — and what the user actually wants — is react to
the real limit hit:

- `routing.strategy: fill-first` + per-credential priority order sends all traffic to the
  top-priority credential until it returns HTTP 429 (limit), then the `cooldown` machinery
  parks it and traffic falls to the next priority; it returns when the cooldown expires.
- `round-robin` (default) / `weighted-round-robin` spread load instead of exhausting one.
- `cooldown.transient-error-cooldown-seconds` and the `retry` block (request-retry rounds,
  max-retry-credentials) govern how failures roll to the next credential. `session-affinity`
  keeps a session pinned to one credential once bound (an established binding outranks
  priority) — leave false unless you want sticky sessions.

State the trigger honestly to the user: fallback fires on real limit-exhaustion (429), not
on a countdown timer — which is more reliable than guessing remaining time.

## Connecting a client (Hermes) to the gateway

The gateway is an OpenAI-compatible endpoint, so point any client at it as a `custom`
provider. For Hermes (co-located on the same Pi, so `127.0.0.1`), set via `hermes config
set` — NEVER hand-edit config.yaml (a stray indent corrupts the live config):

```
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:8317/v1
hermes config set model.api_key <the access.api-keys value>
hermes config set model.default <catalog-model-id> --force
hermes config set agent.reasoning_effort high
```

- The exact model IDs come from `/v1/models` on the gateway (e.g. `claude-opus-5-5`,
  `claude-sonnet-5`, `gpt-5.6-terra`, `gpt-5.6-sol`) — list it first, don't guess names.
- `model.default` set to an ID not in Hermes's built-in catalog needs `--force` (it warns
  otherwise); this is normal for a custom provider.
- Expose extra models as switchable aliases: `hermes config set model.aliases.<name>
  <model-id> --force`, then `/model <name>` in any session (`--global` to persist).
- `agent.reasoning_effort` is global (none|minimal|low|medium|high|xhigh|max|ultra); there
  is no per-alias reasoning, so "sonnet high" + "terra high" just means the global effort
  applies to whichever alias is active.
- VERIFY with a real round-trip, not just the config write:
  `hermes chat -q 'Say OK'` should return through the gateway in a few seconds.

PITFALL: Hermes runs ONE active model per session — it does not blend two models into a
single "combo" response. The only two-model split is main model (`model.default`) +
subagent model (`delegation.model`); if a user asks for a "combo of X and Y", clarify
whether they mean main-vs-delegation, otherwise just give them both as `/model` aliases.
