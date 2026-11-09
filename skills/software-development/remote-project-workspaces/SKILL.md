---
name: remote-project-workspaces
description: "Use when SSH-ing to the Windows PC or syncing it. Alias `pc`, auth traps, remote PowerShell, Syncthing."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, windows]
metadata:
  hermes:
    tags: [ssh, tailscale, windows, git, synchronization, workspace]
    related_skills: [github, codebase-inspection]
---

# Remote project workspaces

## Connection facts (this machine)

The Windows PC is already configured in `~/.ssh/config` as the alias **`pc`**:
`HostName 100.66.73.50` (Tailscale), `User andra`, `IdentityFile ~/.ssh/id_ed25519_pc`,
`IdentitiesOnly yes`. It answers `OpenSSH_for_Windows_9.5`; `hostname` is `AlexA`,
`whoami` is `alexa\andra`; default remote shell is `cmd.exe`.

```bash
ssh -o BatchMode=yes pc 'powershell -NoProfile -Command "hostname; whoami"'
```

Never probe it as `alexa@100.66.73.50` — the Windows account is `andra`, the
Linux-side user is `alexa`, and the Tailscale node name is `alexa`; all three differ.
Guessing the username returns `Permission denied (publickey,password,keyboard-interactive)`,
the exact text of a rejected key, which repeatedly causes the false conclusion that
the PC is unreachable. **Use the alias; it works.** TCP 22 being open plus that error
means wrong username, not wrong key.

## When to Use

Use when a repository may have unpushed changes on another computer, when the
Linux host must inspect a Windows workspace, or when the user asks for a shared
project directory between machines.

This also covers *installing or configuring* anything on the remote PC (tooling,
CLI utilities, shell setup). As soon as a request concerns "my PC" rather than
this host, step 2 applies before you conclude anything about reachability.

## Procedure

0. **Establish WHICH machine the request targets before installing anything.**
   "Set up a nicer terminal", "install this", "make it convenient" from a user
   who reaches this host *over SSH from their own desktop* usually means their
   desktop, not the box you are running on. Installing a full toolchain on the
   wrong machine is silent — every command succeeds — and the whole effort is
   discarded. Ask, or infer from how they connect, before the first install.
   Server-side tooling is still worth keeping when it earns its place for its own
   reason (a multiplexer on the remote host survives dropped SSH sessions);
   say which half is which rather than presenting it as the delivered request.
1. Identify the remote PC from Tailscale peers and record its Tailscale IP,
   hostname, and online state. Test TCP 22 before attempting SSH.
2. **Read `~/.ssh/config` before diagnosing any auth failure.** A `Host` alias set up in an earlier
   session usually already carries the correct `User`, `IdentityFile`, and `IdentitiesOnly` — so
   `ssh user@ip` guessing the username fails while `ssh <alias>` works immediately. Without
   `IdentitiesOnly yes` plus an explicit `-i`, SSH offers only the *default* key and never tries the
   host-specific one, which reads as a rejected key when the key was simply never sent. Check the
   offered-vs-accepted lines before touching the server:
   ```bash
   search_files '' --target files --path ~/.ssh      # read config, note Host/User/IdentityFile
   ssh -vv -o BatchMode=yes <alias> true 2>&1 | grep -iE 'remote software|Offering|Authentications that can continue|Server accepts key'
   ```
   `Server accepts key` is the proof; `Offering` alone is not. Only after the alias itself fails is
   the wrong-username / wrong-authorized-keys-location diagnosis worth pursuing.

   The username is the trap worth naming: a Windows account name frequently differs from the machine
   hostname *and* from the Linux-side username, so `ssh <linux-user>@<ip>` fails with
   `Permission denied (publickey,password,keyboard-interactive)` — the same text a genuinely rejected
   key produces. Never conclude "the key is rejected" from that string alone; it is equally the
   signature of asking for an account that does not exist. Resolve the real account from the alias
   in `~/.ssh/config`, not by guessing.

   Read the config **first**, not after a failure. One wrong-username attempt returning
   `Permission denied` is enough to produce the false report "I have no credentials / cannot reach
   the PC" and divert the whole task into handing the user manual instructions, while a working
   alias sat in the config the entire time. Checking a password vault is not a substitute: SSH key
   auth stores nothing there, so an empty vault says nothing about access.
3. If SSH is reachable, inspect the PC repository directly with `git status
   --short --branch`, `git remote -v`, `git branch -vv`, `git log --oneline -12`,
   and `git diff --stat`. Compare its HEAD and working tree with the intended
   remote branch before pushing anything.
3. If the PC is unreachable or powered off, inspect only the Linux clone and
   GitHub remote. State explicitly that a clean Linux clone cannot prove the PC
   working tree is clean. For an Obsidian vault, inspect its installed Git plugin
   settings before recommending new sync machinery: `autoSaveInterval`,
   `autoPullOnBoot`, and `pullBeforePush` determine whether desktop changes
   actually commit, pull, and push. A configured interval and a matching remote
   ref prove configuration and delivery from the inspected clone, not that the
   plugin timer fired or the inaccessible PC pulled. Verify a two-way test note
   on both machines before calling cross-device sync complete; avoid concurrent
   edits to the same note because Git may require manual conflict resolution.
4. Push only commits actually present in the inspected clone. Verify the remote
   ref with `git ls-remote` after pushing; never claim unseen PC changes were
   synchronized.
5. When the task is narrow (install a tool, add one file) but the repo already
   has unrelated WIP changes from other work, never `git add -A && git commit`
   blind — that bundles unrelated edits (and local-only files like
   `.claude/settings.local.json`) into your commit. Stage everything, then
   `git restore --staged <paths not part of this task>`, and commit with
   `git commit -m "..." -- <explicit paths>` so the commit is scoped even if
   something is still staged. Confirm with `git diff --cached --stat` before
   committing.
6. If `git commit` fails with `Author identity unknown` on a shared/fresh box,
   match the repo's existing author instead of inventing one — a mismatched
   identity on a single-owner repo pollutes `git log` attribution:
   ```bash
   NAME_EMAIL=$(git log -1 --format='%an|%ae')
   git config user.name "${NAME_EMAIL%%|*}"
   git config user.email "${NAME_EMAIL##*|}"
   ```
   Set it locally (no `--global`) since the box may be shared across repos/owners.
5. Prefer Git as source of truth and Syncthing for optional file synchronization.
   Keep active Node projects on local disks; do not use an SMB/network mount as
   the primary `node_modules` or build tree because watching, permissions, and
   performance are unreliable.
6. For any Syncthing "disconnected" complaint, read the service journal for the
   peer name and `reject` lines *before* changing addresses, discovery, or
   firewall settings, then drive all repairs through the local REST API rather
   than asking the user to open the GUI. See
   `references/syncthing-peering.md` for the endpoints, the
   reinstalled-peer/new-device-ID root cause, and the completion checks that
   actually prove a sync finished.
7. If the PC may be offline, keep a runnable clone on Linux and record its
   environment separately. Do not assume Windows-only services, Docker Desktop,
   WSL paths, or secrets exist on Linux; verify prerequisites before starting a
   repository.
8. When the PC is being used to **host a backing service** for the Linux host
   (a database, broker, or anything the Pi lacks the RAM for), read
   `references/windows-remote-services.md` first. It covers the two failures
   that waste the most turns: a GUI-backed stack such as Docker Desktop cannot
   start from a non-interactive SSH session, and a foreground server is killed
   when the session closes, so it must be registered as a service.

## Windows SSH Setup

Use either Windows OpenSSH Server with TCP 22 allowed only through the Tailscale
address, or Tailscale SSH with suitable account/ACL access. Never expose an
unauthenticated public SSH port. Use key authentication or Tailscale identity
controls and never request passwords in chat.

### OpenSSH Server with an administrative Windows account

1. Generate a dedicated ed25519 key on Linux; do not reuse the key for unrelated
   services. Install OpenSSH Server, start `sshd`, set it to automatic startup,
   and add a firewall rule restricted to `100.64.0.0/10`.
2. Identify the *actual* Windows account before testing — the machine hostname
   and Tailscale node name are not SSH usernames. Connect with the dedicated key
   and `BatchMode=yes`; never fall back to a password prompt.
3. For an account in the local Administrators group, put the public key in
   `C:\ProgramData\ssh\administrators_authorized_keys`, not merely the user's
   `.ssh\authorized_keys`; the default `Match Group administrators` configuration
   selects the system file. Lock its ACL to `SYSTEM` and `Administrators`, then
   restart `sshd`.
4. Configure a Linux SSH alias with `HostName`, `User`, `IdentityFile`, and
   `IdentitiesOnly yes`. Test `ssh <alias> "echo CONNECTED && hostname && whoami"`
   before relying on it for repository work.
5. Keep Windows remote commands shell-simple. Use `cmd /c` for filesystem and
   git probes, or invoke one self-contained PowerShell command; nested quotes
   and unescaped PowerShell pipelines sent through SSH are easily interpreted by
   `cmd.exe` instead of PowerShell.
6. When a probe needs more than one PowerShell statement, **write a `.ps1`, `scp` it, and run it
   with `-File`** rather than escalating the escaping. Two layers of quoting (local shell → remote
   `cmd.exe` → PowerShell) silently collapses `$var` and nested quotes, and the symptom is empty
   output with exit code 0 — which looks like "nothing found" rather than a broken command:
   ```bash
   scp -o BatchMode=yes probe.ps1 <alias>:/Users/<user>/probe.ps1
   ssh -o BatchMode=yes <alias> 'powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\<user>\probe.ps1'
   ```
   Treat empty-plus-exit-0 from a remote one-liner as an escaping failure to retry as a script, never
   as a negative result about the remote machine.
7. **Identify remote processes with `Get-CimInstance Win32_Process`, not `wmic`.** `wmic` is removed
   from current Windows builds and exits 0 with no output, which reads as "no such process" instead
   of "no such tool":
   ```powershell
   Get-CimInstance Win32_Process -Filter "ProcessId=<pid>" |
     Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | Format-List
   ```
   The `CommandLine` plus `CreationDate` pair is what identifies an unknown process: it reveals the
   module, profile, and start time, which is how you tell a stray hand-started script from a
   long-running service. Walk `ParentProcessId` once to find what launched it.
8. **Resolve app data roots from the environment, not from `$env:USERPROFILE\.hermes`.** Windows apps
   commonly live under `$env:LOCALAPPDATA\<app>`, so probing the Unix-style dotfile path finds an
   empty or absent directory and invites the false conclusion that the app has no config or jobs at
   all. Probe both roots before reporting nothing was found.
9. Avoid `Get-Content -Raw` in probes meant to run on any PowerShell the box may have — the
   parameter is missing on older hosts and the whole script dies on that line. Use
   `[IO.File]::ReadAllText($path)` for whole-file reads, and `Out-String -Width <n>` on tabular
   output so columns are not truncated at the default console width.

### Verifying a downloaded Windows installer

Vendors like Apple publish no checksums, so a hash matches nothing authoritative and a "known good"
hash from a forum is just someone else's copy. Verify the **Authenticode signature**, which cannot be
forged and is checkable offline; report the hash only as an identity fingerprint:

```powershell
$f = "$env:USERPROFILE\Downloads\<installer>.exe"
$s = Get-AuthenticodeSignature $f
"STATUS: " + $s.Status                                  # want Valid
"SIGNER: " + $s.SignerCertificate.Subject               # want the real vendor O=
"SHA256: " + (Get-FileHash $f -Algorithm SHA256).Hash
```

When the question is really "is my tooling healthy", also enumerate installed vendor software and
service state in the same script — `Get-ItemProperty` over both `Uninstall` hives filtered by
`Publisher`, `Get-AppxPackage` to catch a Microsoft Store variant that shadows the desktop build, and
`Get-Service` for the device-support service. That distinguishes a bad download from a bad install
from a healthy host, which a hash alone never does. Non-ASCII entries in the Uninstall hive may come
back mojibake over SSH; that is a console codepage artifact, not a corrupt install.

A public-key failure after TCP connects usually means either the wrong Windows
username or the wrong authorized-keys location; verify both before changing
firewall or Tailscale settings.

Two more symptoms that look like a server fault and are not:

- **An empty SSH banner** when probing with `/dev/tcp` proves nothing. Windows OpenSSH does not emit
  its version line to a bare TCP read the way a shell probe expects; read the software version from
  `ssh -vv` (`remote software version OpenSSH_for_Windows_x.y`) instead of concluding the port is
  answered by something other than sshd.
- **A command echoed back verbatim** (`hostname; whoami` returning the literal string) means the
  remote default shell is `cmd.exe`, which does not understand `;`. That is a shell mismatch, not a
  broken session — switch to one `powershell -NoProfile -Command` invocation, or a `.ps1` run with
  `-File` for anything multi-statement.

## Probing Windows tooling state

Before recommending installs, enumerate what the PC already has instead of
inferring it from package-registry searches. One `.ps1` beats a dozen web
lookups: iterate candidate commands through `Get-Command` and print
present-vs-missing, then add `Get-Module -ListAvailable` for shell modules and
`Test-Path $PROFILE`. A missing profile means no shell configuration exists at
all, which changes the recommendation from "install a tool" to "set up the
shell" — and `PSReadLine` below 2.3 means predictive IntelliSense is unavailable
regardless of what else is installed. Note that `$PROFILE` under
`powershell.exe` (5.1) resolves to `WindowsPowerShell\`, a *different* file from
`pwsh` 7's `PowerShell\`; confirm which shell the user actually launches before
writing to either.

## Verification

A repository audit must distinguish local working-tree changes, local commits
not on the remote, and remote commits not present locally. For web projects,
inspect the actual source tree for SEO routes (`sitemap`, `robots`), metadata
generation, canonical URLs, Open Graph, and structured data instead of inferring
them from memory or a previous report.

## Reporting

Keep the report short: connection state, repository state, what was pushed, and
what remains. The user prefers results over progress narration; do not stream
command-by-command updates.

When a fault is fixed, lead with the actual root cause in one sentence, then what
was changed, then the verified end state with concrete numbers (file counts,
sizes, completion percent, error counts). Never report "connected" or "done" from
a liveness signal alone — query the state that proves the work finished, because
a peer can be connected and still sharing nothing.

## References

- `references/syncthing-peering.md` — Syncthing REST API diagnosis, device-ID
  rotation after a peer reinstall, folder re-sharing, verification endpoints.
- `references/windows-remote-services.md` — hosting a service on the PC for the
  Linux host: interactive-session limits, registering a service so it survives
  SSH, portable archives over vendor installers, and the LAN-vs-tailnet source
  address that breaks host-based auth.
