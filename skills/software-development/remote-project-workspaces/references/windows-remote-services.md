# Provisioning services on the Windows PC over SSH

For when the Linux host needs a database, broker or other backing service
running on the Windows PC (more RAM than the Pi) and reachable over Tailscale.

## An SSH session is not an interactive desktop session

SSH lands in its own non-interactive session, while the logged-in desktop owns
another (`tasklist /FI "IMAGENAME eq explorer.exe"` shows its session number).
Anything requiring a desktop session — Docker Desktop and other tray GUIs —
starts, runs for seconds, and exits with no error written anywhere. Symptom: the
process appears in `tasklist` on first check and is gone from the next one,
memory never growing.

So prefer a service or a plain daemon over any GUI-backed stack, and when the
GUI genuinely is required, ask the user for one click on the machine instead of
burning turns on relaunch attempts. Confirm the diagnosis before switching
approach: start it, wait ~25s, re-check `tasklist`.

For Docker specifically, `com.docker.service` can be started over SSH
(`net start com.docker.service`) and WSL can be revived with `wsl --shutdown`
followed by any `wsl -d <distro> -- echo ok`, but the engine still does not come
up while the `docker-desktop` WSL distro stays `Stopped` — that distro is the
one the GUI launches. Check `wsl -l -v` to tell "platform broken" from "GUI
never started".

## A foreground server dies with the SSH session

`pg_ctl start`, `node server.js` and friends are children of the SSH session, so
they are killed when it closes even with output redirected. The log shows a
clean successful startup and the port is simply gone afterwards. Register a real
service instead:

```cmd
C:\pg17\pgsql\bin\pg_ctl.exe register -N pg17svc -D C:\pg17\data -o "-p 5432"
net start pg17svc
```

Verify with `netstat -ano | findstr :5432`, never with the log line
`database system is ready to accept connections` — that is printed before the
process is reaped, so it is true and useless.

## Prefer portable archives to vendor installers

EnterpriseDB-style (Bitrock) installers fail in silent mode without mandatory
arguments such as `--superpassword`, `--serverport` and `--datadir`; `winget`
does not pass them, so the install exits `1` with no log and an empty target
directory. The vendor's portable binaries zip needs no installer, no admin
rights and no interactive session. Extract, `initdb`, register the service.

`initdb` fails on a non-English Windows locale (`Ukrainian_Ukraine.1251` cannot
pair with UTF8). Pass `--locale=C` with `-E UTF8`. Afterwards it still prints a
collation *warning* in the console language — check for `data/PG_VERSION` to
see whether the cluster was actually created rather than reading the message.

Write these multi-step flows as a `.ps1` and run with `-File` (see SKILL.md):
also make them idempotent, because provisioning is always retried after one
step fails. Guard each stage on its artifact (`PG_VERSION`, the archive, the
binary) and do not branch on localized CLI output — `pg_ctl status` prints
"no server running" in the console language, so an English regex silently skips
the start step.

## Reaching the service from the Linux host

Two separate gates, and failing either looks the same from the client:

1. Listener and firewall: bind `0.0.0.0` (for Postgres
   `listen_addresses = '*'`) and add an inbound rule
   (`New-NetFirewallRule -LocalPort <port> -Protocol TCP -Action Allow`).
2. The service's own host-based auth.

A Tailscale peer on the same LAN connects over the **direct LAN route**, so the
source address the service sees is the private LAN IP, not the tailnet
`100.64.0.0/10` address — check `tailscale ping <peer>`, which names the path
(`via 192.168.x.y:41641`). Authorizing only the tailnet address yields a TCP
connect that immediately resets, so `/dev/tcp` reports the port open while the
client reports a connection failure. Authorize both ranges in `pg_hba.conf`
(`100.64.0.0/10` and the LAN `/24`) and `pg_ctl reload`.

Prove the hop with the real client library rather than a port probe, and run it
a few times to get a latency baseline — a working handshake plus a known RTT is
what lets you attribute a later "connection timed out" to the application
rather than the link.
