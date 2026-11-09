---
name: headless-linux-remote-admin
description: "Find, SSH into, and debug a headless Linux box (Pi, server)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ssh, raspberry-pi, linux, networking, tailscale, vpn, troubleshooting, homelab]
---

# Headless Linux Remote Admin

Find a headless box on the network, get a shell on it safely, and diagnose why a
service on it can't reach the internet. Built for Raspberry-Pi / home-server work.

## When to Use

- You need to locate a Raspberry Pi / home server on the LAN and SSH into it.
- A service on a remote Linux box (Tailscale, Docker, apt) can't reach the internet
  while the box is otherwise on the network.
- A VPN was disconnected/removed and connectivity broke afterward (routing/DNS residue).

## 1. Find the host on the LAN

1. Get your own subnet + gateway: `ipconfig` (Windows/git-bash) or `ip addr`. The
   LAN is usually `192.168.x.0/24` via the listed Default Gateway.
2. Check `arp -a` first — hosts you've talked to are already cached, no scan needed.
3. Cross-reference `~/.ssh/known_hosts` — a box you've SSHed before is listed by IP;
   that plus an open port 22 is near-certain identification.
4. If a mesh VPN is configured, `tailscale status` from ANY node lists the target
   with its last-seen time. `offline, last seen Nd ago` means the target's daemon is
   up locally but logged out / cut off from its control plane — go in over the LAN IP
   to fix it, not over the (dead) VPN address.
5. Confirm SSH is open before trying to log in: `(echo > /dev/tcp/<ip>/22) && echo OPEN`.
   Pi MAC OUIs (B8:27:EB, DC:A6:32, D8:3A:DD, E4:5F:01, 28:CD:C1, 2C:CF:67) help ID a Pi
   in `arp -a`, but a Pi behind a firewall may show none of these — port 22 + known_hosts
   is the reliable signal.

Pitfall: a sequential `ping` sweep of a /24 in git-bash/foreground times out long before
it finishes. Rely on the ARP cache and a targeted port-22 check instead of sweeping.

## 2. Get a shell — never put the password in chat

If key auth fails (`Permission denied (publickey,password)`) you need password login.
Do it through an interactive PTY so the password goes to SSH, never into the transcript:

1. Start the session backgrounded in a PTY:
   `terminal(background=true, pty=true, command="ssh -tt -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=accept-new <user>@<ip>")`
2. Use the returned `session_id` with `process(action='poll')` until you see `<user>@<ip>'s password:`; do not start a second SSH process while the first is waiting, because the password prompt belongs to that PTY.
3. Send the password with `process(action='submit', session_id='<id>', data='<pw>')` — submit appends the Enter a Windows PTY needs;
   a bare newline via `write` is NOT delivered as a line terminator on Windows PTYs.
4. Poll again for the shell prompt.

After login, add your pubkey to `~/.ssh/authorized_keys` on the host so future sessions
skip the password entirely. If the user typed a password/PIN into chat, remind them it's
now in history and to rotate it.

## 3. Migrate Hermes state without exposing secrets

When copying Hermes configuration or memory from a workstation to the remote box:

1. Resolve the active local Hermes home from `$HERMES_HOME`, not `~/.hermes` when the profile uses a non-default home.
2. Copy only the requested non-secret files, typically `config.yaml` and `memories/MEMORY.md`; exclude `.env`, `auth.json`, vault data, OAuth tokens, and session databases unless the user explicitly approves each category.
3. Before overwriting remote files, create a timestamped backup of the target files on the remote host and preserve their ownership and mode.
4. Transfer through the already-authenticated SSH connection (for example, `scp` or an SSH tar stream), then verify remote file hashes and inspect the resulting provider/base URL settings. Do not report completion until the remote files are readable and the expected model/provider entries are present.
5. If SSH is waiting for a password, keep driving the interactive PTY with `process(action='submit')`; do not abandon the transfer and tell the user to run SSH manually unless the PTY path itself is unavailable. Never accept a password in chat.

Keep secrets local by default: a copied config may reference an environment variable that must be provisioned separately on the remote host, but do not copy the value implicitly.

## 3b. Share a working tree between workstation and box

For "make a shared folder between the PC and the Pi", do NOT start by enabling an SSH
server or SMB share on Windows — that is the path that needs elevation and stalls. Use
peer-to-peer Syncthing over the mesh VPN; full procedure, REST calls, hardening and the
JSON/`.stignore` pitfalls are in references/pc-pi-file-sync.md.

## Reporting style for long remote setups

This user wants the result, not the journey. While a multi-minute step runs (large first
scan, apt install, build), say in one line what is running and that it continues in the
background, instead of silently polling for several turns — unexplained silence reads as
a hang and draws "what is taking so long". Finish with a short plain-text block: what is
now working, then the one or two things left for the user to do, with the exact command
to paste. No narration of the intermediate attempts.

## 4. Diagnose broken outbound connectivity from a service

When a service (Tailscale, Docker, apt, etc.) can't reach the internet but the box
is clearly on the LAN, work outward and localize the layer:

1. **Raw reachability:** `ping -c2 1.1.1.1` — is IPv4 routing alive at all?
2. **DNS:** `cat /etc/resolv.conf` and `getent hosts <target-domain>`. Stale VPN DNS
   servers (e.g. NordVPN's `103.86.x.x`) left in `/etc/resolv.conf` resolve domains to
   addresses the box can't actually route to. `/etc/resolv.conf` is often a plain file a
   VPN client overwrote and never restored — NetworkManager knowing the right DNS
   (`nmcli -g IP4.DNS ...`) does NOT mean it wrote that file. Fix by writing working
   resolvers directly: `printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\n' | sudo tee /etc/resolv.conf`.
3. **IPv4 vs IPv6 split-brain:** if `getent` returns IPv6 addresses but `ip -6 route show default`
   is empty, the daemon dials dead IPv6 and logs `network is unreachable`, while `curl -4`
   to the same host succeeds. A home router that sends no Router Advertisements
   (`ping -6 ff02::2%<iface>` = 100% loss, no RA in `journalctl -k`) does not provide global
   IPv6 — you cannot "restore" it on the host; the address comes from the router. Leaving IPv6
   disabled is fine; the real fix is almost always DNS or routing below, not IPv6 itself.
4. **Policy-routing AND firewall residue (the big one):** `ip rule show` + `ip route show table <N>`,
   AND `sudo nft list ruleset`. See references/vpn-routing-residue.md — a disconnected VPN routinely
   leaves `ip rule` entries and fwmark rules pointing at an empty/`unreachable` table that silently
   blackhole all un-marked traffic, even though `curl` occasionally slips through. It ALSO leaves an
   orphan nftables killswitch table (`table inet nordvpn`) that drops non-tunnel egress with
   `operation not permitted` — invisible to `iptables -S`, so always check `nft list ruleset` too.
5. **Service-level probe:** for Tailscale, `tailscale netcheck`. `UDP: false` +
   `IPv4: (no addr found)` + `Nearest DERP: unknown` while plain HTTPS works = the daemon's
   own packets are being blackholed by routing/firewall residue, not a control-plane outage.

### Tailscale-specific

- `tailscale status` → `Logged out.` with `tailscale debug prefs` showing `WantRunning: true,
  LoggedOut: false` means the node key expired (common ~after weeks) — the daemon wants to run
  but the control plane rejects it. Re-auth with `tailscale up`.
- `tailscale up` that hangs and prints NO login URL (`doLogin(hasUrl=false)` in
  `journalctl -u tailscaled`) is not a Tailscale bug — the daemon can't reach the control
  plane at all. Fix the DNS / routing residue in step 3 FIRST; the URL only appears once the
  daemon can talk out.
- The daemon (Go) uses its own resolver, so pinning `/etc/hosts` or editing `gai.conf` does
  not reliably steer it — and pinning a single anycast control-plane IP in `/etc/hosts` can
  make it worse when that IP times out. Fix DNS at `/etc/resolv.conf` and clear bad routes
  instead.

## Tailscale + another VPN (e.g. NordVPN) coexistence

- They CAN coexist as mesh-only: Tailscale routing just its `100.x` CGNAT range while the
  other VPN carries the default route. They CONFLICT when both try to be exit-node /
  full-tunnel — two services fight over `0.0.0.0/0` and one loses.
- The real-world failure is not incompatibility, it's the other client not cleaning up its
  `ip rule` / DNS / interface on disconnect. For an always-on box (bot/server) run only
  Tailscale and keep the other VPN inactive; that removes the whole class of blackhole.
