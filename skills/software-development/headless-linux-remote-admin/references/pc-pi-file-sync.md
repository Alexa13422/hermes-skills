# Two-way file sync between a Windows workstation and a headless Linux box

Use this instead of SMB/sshfs when the shared tree holds Git or Node projects: a
network mount as the single source of truth is slow and corrupts permissions and
`node_modules`. Sync peer-to-peer and keep a real local copy on each side.

## Why not SSH-from-Linux-to-Windows first

On Windows, `tailscale set --ssh` is rejected outright ("Tailscale SSH server is not
supported on windows"), and installing OpenSSH Server plus the port-22 firewall rule
needs elevation — `Get-WindowsCapability` and `New-NetFirewallRule` both fail with
"requires elevation" from a normal agent shell. So do NOT make inbound SSH to Windows
a prerequisite: Syncthing needs no admin rights and no inbound port the user must open.
Workstation -> box SSH stays available and is enough for all remote driving.

## Procedure

0. Audit the existing Windows node before installing or reconfiguring it. Syncthing may already be running even when it is absent from `PATH`:
   - `netstat -ano | grep ':8384'` identifies the listening PID; confirm with `tasklist.exe /FI "PID eq <pid>"`.
   - Read `%LOCALAPPDATA%/Syncthing/config.xml` for the GUI API key and query `GET /rest/system/connections` and `GET /rest/config/folders` with `X-API-Key`. An empty `connections` object means no current peer; an empty folders array means the local sharing definition was lost, not merely disconnected.
   - Do not reinstall or overwrite this configuration before this audit: doing so changes the node Device ID and requires re-authorizing it on every peer.
1. Windows side, no installer, no admin: fetch the real latest build — the
   `releases/latest/download/...-v<version>.zip` URL 404s because the filename carries
   the version. Resolve it first:
   `curl -s https://api.github.com/repos/syncthing/syncthing/releases/latest | grep -o '"browser_download_url": "[^"]*windows-amd64[^"]*"'`
   Unzip into `$LOCALAPPDATA/Syncthing`, then run
   `./syncthing.exe serve --no-browser --home="$LOCALAPPDATA/Syncthing/config"`.
2. Linux side: `sudo apt-get install -y syncthing` and
   `sudo systemctl enable --now syncthing@<user>` (the `@user` unit, so the daemon owns
   the user's files).
3. Collect both identities non-interactively:
   - device ID: `syncthing.exe --home=<home> device-id` (Windows) / `syncthing --device-id` (Linux)
   - API key: `grep -o 'apikey>[^<]*' <config-dir>/config.xml` (Linux 2.x path is
     `~/.local/state/syncthing/config.xml`, not `~/.config/syncthing`)
4. Configure both ends over the REST API rather than the GUI — everything is
   `-H "X-API-Key: <key>"` against `http://127.0.0.1:8384`:
   - First fetch the full configuration from each side with `GET /rest/config`; preserve
     the existing device/folder objects rather than constructing minimal JSON, because
     Syncthing validates full configuration fields.
   - Replace a stale peer Device ID everywhere it occurs: in the peer `devices` list AND
     every shared folder's `devices` list. A reinstalled/reset node gets a new Device ID;
     adding its new ID only on one peer leaves both nodes known but disconnected.
   - Update each entire config with `PUT /rest/config`, then restart each instance via
     `POST /rest/system/restart`. Verify that both endpoints now list the other node's
     current Device ID before diagnosing networking.
   - Give the peer `addresses` ordered as `["tcp://<peer-tailscale-ip>:22000",
     "tcp://<peer-lan-ip>:22000","dynamic"]`. Syncthing chooses the best reachable
     path, so it uses fast direct LAN while available and Tailscale when the LAN path is
     absent; retain `dynamic` as an additional fallback.
   - Keep the SAME folder `id` on both hosts, `type` `sendreceive`, both current device
     IDs, `fsWatcherEnabled: true`, and `ignorePerms: true`. Mutual configuration is
     what authorizes the share; no click-through is needed when both sides are changed.
5. Verify with real state, not assumptions:
   - `GET /rest/system/connections` -> peer `connected: true` plus a `TLS1.3-...` crypto string.
   - `GET /rest/db/status?folder=<id>` -> `state`, `localFiles`, `needBytes`.

## Pitfalls

- Pass JSON bodies from a FILE (`--data-binary "@C:/path/body.json"`), not inline, when a
  Windows path is involved: `"path":"C:\\Programming"` inside a shell-quoted `-d` string
  makes Syncthing reject the request with ``invalid escape sequence `\P` in string``. Use
  forward slashes (`C:/Programming`) in the folder path. git-bash curl also needs the
  native `@C:/...` form — `@/c/...` fails to open.
- Exclude build output on BOTH sides via a `.stignore` in the folder root
  (`(?d)node_modules`, `.next`, `dist`, `build`, `target`, `obj`, `.venv`, `.anchor`,
  `*.log`) — otherwise the first scan indexes six-figure file counts and the box with
  less RAM thrashes.
- The first scan of a large tree takes many minutes and reports `state: scanning` with a
  climbing `localFiles`. That is progress, not a hang: say so and move on instead of
  polling in silence.

## Hardening the pair

- `PATCH /rest/config/options` with
  `{"globalAnnounceEnabled":false,"relaysEnabled":false,"natEnabled":false,"localAnnounceEnabled":true,"urAccepted":-1,"crashReportingEnabled":false}`
  on both hosts: the nodes stop appearing in the public discovery pool and only talk over
  LAN / mesh VPN, while transport stays TLS1.3 with device-ID pinning.
- `PATCH /rest/config/gui` with `{"address":"127.0.0.1:8384"}` so the admin API is not
  exposed on the LAN.
- Autostart without admin on Windows: drop a `.vbs` one-liner that `Run`s
  `syncthing.exe serve --no-browser --home=...` with window style `0` into
  `%APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup`. A Scheduled Task or service
  would need elevation; the Startup folder does not.
- Linux SSH hardening that does not lock you out: write a drop-in
  `/etc/ssh/sshd_config.d/99-hardening.conf` with `PermitRootLogin no`, `MaxAuthTries 3`,
  `X11Forwarding no`, `ClientAliveInterval 300`, then `sshd -t && systemctl reload ssh`.
  Install `fail2ban` for brute-force protection. Keep `PasswordAuthentication yes` until
  key login is PROVEN with
  `ssh -o PreferredAuthentications=publickey -o BatchMode=yes <user>@<host> true`.
- If the user later wants inbound SSH to Windows, hand them the elevated three-liner and
  scope the firewall rule to the mesh range only:
  `New-NetFirewallRule -Name sshd-ts -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow -RemoteAddress 100.64.0.0/10`.
