# Making a project always-on and reachable over Tailscale

Two separate problems the user usually asks for together: "run this always" and
"let me open it from my phone". Solve them with systemd + Tailscale Serve, not by
binding the app itself to a non-loopback address.

## 1. systemd unit per long-running process

One unit per logical process (collector, admin/API, worker) rather than one
mega-unit — independent restart/status/logs, and a crash in one does not take
down the other.

```ini
[Unit]
Description=<project> - <role>
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<user>
WorkingDirectory=/path/to/project
EnvironmentFile=/path/to/project/.env
ExecStart=/path/to/venv/python -m project --config config.toml <subcommand>
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`sudo cp` into `/etc/systemd/system/`, `daemon-reload`, then
`enable --now <unit1> <unit2>` — enable survives reboot, `--now` starts it this
session without a separate `start`.

**`EnvironmentFile=` requires clean line endings.** A `.env` edited on Windows or
pasted through some clipboard paths picks up CRLF; systemd silently fails to
parse the affected line (the value grows a trailing `\r`, breaking downstream
consumers in confusing ways rather than erroring loudly). Strip it before first
use and whenever the file is touched from a non-Linux source:
```bash
sed -i 's/\r$//' .env
```

## 2. Exposing a loopback-only admin/API without touching its bind address

When the app deliberately binds only `127.0.0.1` (commonly because it has no
auth and relies on loopback-only reachability as its security boundary), do NOT
"fix" this by rebinding it to the Tailscale IP or `0.0.0.0` — that removes the
only access control it has. Use Tailscale Serve as a reverse proxy instead; the
app's bind address and security model stay untouched:

```bash
sudo tailscale serve --bg <local-port>
tailscale serve status   # confirm the proxy entry
```

This publishes `https://<tailnet-hostname>.<tailnet>.ts.net/` for every device in
the same tailnet — functionally equivalent reachability to binding the Tailscale
interface directly, but Tailscale terminates TLS and owns the exposed surface
rather than the app itself.

If `serve` reports "Serve is not enabled on your tailnet", it returns an enable
URL and the command keeps running in the background waiting for that one-time
tailnet-admin approval — poll the backgrounded command's output rather than
assuming it failed; it often completes and starts proxying once approved,
without re-running the command.

To take it back down: `sudo tailscale serve --https=443 off`.

## Pitfalls

- **Don't ask "why" if the user already has a precedent in the same tailnet** (an
  existing tool bound to `0.0.0.0` reachable at the Tailscale IP). That precedent
  is the user's own risk tolerance for THAT app, not a blanket license to rebind
  every service the same way — an app with no auth is a different risk than one
  that already assumes network-level trust. Offer the Serve proxy as the default
  and only bind-direct if the user explicitly says the app's own auth (or absence
  of one) is acceptable to expose directly.
- **Verify what actually changed, not what the agent claims changed.** After a
  delegated/background code change to a UI or responsive layout, independently
  render it (see the dogfood-style headless-Chromium + vision_analyze combo in
  `software-development/dogfood`) at the real target viewport and re-run the full
  test suite yourself — a coder subagent's own self-report of "no horizontal
  scroll" is not evidence.
- **Grep the database for stale rows before trusting what a dashboard displays.**
  A UI can be fully rewritten and still show old-looking content if a prior
  module wrote rows into a table that the current code never updates or deletes
  (e.g. a removed feature's status/log rows lingering in a shared table). Find
  every write site for the field in question (`grep` the exact column/table
  across the current codebase); if nothing writes it anymore, the data is dead
  and belongs in a one-time cleanup migration, not a UI filter.
