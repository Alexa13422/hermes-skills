---
name: raspberry-pi-operations
description: "Use when operating a Raspberry Pi. Check health."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [raspberry-pi, hardware, swap, thermal, tailscale, vpn, hosting]
    related_skills: [service-and-credential-provisioning, demo-deployment-readiness]
---

# Raspberry Pi operations

Use this for health checks, unexplained reboots, resource pressure, swap
provisioning, cooling verification, VPN/Tailscale coexistence, and judging
whether the Pi can host a given project.

## Diagnose an unexplained reboot

1. Establish the reboot time and current boot identity:
   ```bash
   uptime
   who -b
   journalctl --list-boots
   ```
2. Check whether a prior boot journal exists before attributing cause:
   ```bash
   journalctl -b -1 -p warning --no-pager
   journalctl -b -1 -n 80 --no-pager
   ```
3. Inspect current hardware state and boot errors:
   ```bash
   vcgencmd measure_temp
   vcgencmd get_throttled
   dmesg -T | grep -iE 'out of memory|oom|panic|watchdog|lockup|under-voltage|voltage|overheat|thermal'
   ```
4. Check memory, load, swap, processes, disk capacity, and service restart counts before diagnosing overload:
   ```bash
   free -h; uptime; swapon --show; df -h /
   ps -eo pid,comm,%cpu,%mem,rss --sort=-%mem | head -20
   systemctl --failed --no-pager
   ```
5. State uncertainty explicitly. If there is no previous journal and no orderly shutdown record, the evidence supports an abrupt reset (power loss, hardware watchdog, or hard reset), not a specific root cause.

Enable persistent journals after confirming sufficient disk capacity so the next incident is diagnosable:
```bash
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
journalctl --flush
```

Do not label a reboot as an OOM event unless the previous journal or kernel log contains an OOM record; ordinary OOM normally kills a process rather than rebooting the host.

## Add NVMe-backed swap safely

First inspect existing swap. Raspberry Pi OS may already use zram; retain it at higher priority because compressed RAM is faster than NVMe.

```bash
swapon --show
df -h /
grep -vE '^\s*(#|$)' /etc/fstab
```

Create and activate a persistent swapfile only where free space comfortably exceeds its size:
```bash
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon -p 10 /swapfile
printf '\n/swapfile none swap sw,pri=10 0 0\n' | sudo tee -a /etc/fstab
sudo systemctl daemon-reload
swapon --show
sudo findmnt --verify --tab-file /etc/fstab
```

Use a lower priority than zram (for example zram 100 and disk file 10) so disk swap is a fallback. Verify both the live activation and generated `swapfile.swap` unit; editing fstab without `daemon-reload` leaves systemd using its prior generated configuration.

When asked whether using more swap will speed up a running job, measure `free -h`, `swapon --show`, `vmstat 1 5`, and the **actual worker** via `ps -eo pid,ppid,rss,stat,comm --sort=-rss` before tuning. Swap extends capacity, not memory bandwidth; sustained `si`/`so` and I/O wait mean paging is already costing time. Do not try to fill swap to accelerate the job. Check the child process rather than only the launcher (`uv` or a shell can have tiny RSS while its Python child consumes most RAM); first compare throughput and paging, then reduce concurrency only if resource pressure is actually constraining progress.

## Verify cooling hardware

Inspect live temperature, throttling, thermal cooling state, fan tachometer, and PWM rather than judging fan operation by audibility:
```bash
vcgencmd measure_temp
vcgencmd get_throttled
for d in /sys/class/thermal/cooling_device*; do
  echo "-- $d"; cat "$d/type" "$d/cur_state" "$d/max_state"
done
for h in /sys/class/hwmon/hwmon*; do
  echo "-- $(cat "$h/name" 2>/dev/null)"
  for f in "$h"/fan*_input "$h"/pwm* "$h"/temp*_input; do
    [ -e "$f" ] && printf '%s=' "$(basename "$f")" && cat "$f"
  done
done
```

A nonzero `fan1_input` confirms physical rotation; `pwm1` shows current duty level. A quiet fan at low temperature can be working normally. Treat `throttled=0x0` as no currently recorded undervoltage or thermal throttling flags.

## Judging whether the Pi can host a project

Answer from measurements taken on the host, not from the RAM figure. Memory
matters for BUILDS; a built Node/Next app serves on 100–200 MB, so several fit
in 4 GB. Check what actually constrains it:

```bash
free -h; swapon --show; nproc; df -h /
lsblk -d -o NAME,SIZE,ROTA          # NVMe vs SD card dominates perceived speed
ps -eo rss,cmd --sort=-rss | head -8
```

Before recommending optimizations, name the current largest consumer — a
desktop browser left running often outweighs every project on the box, and
closing it beats any code change. Distinguish Pi 4 from Pi 5 and SD from NVMe
explicitly; the user's own assumption about their model may be wrong.

Say plainly where the Pi will not do: native toolchain builds (Rust/Anchor),
several parallel bundler builds, or a full app-plus-database-plus-cache stack.
For a public demo that must stay reachable, prefer managed hosting over the Pi
and say why (no dependency on the Pi being powered or the home link being up);
keep the Pi for private or always-on internal stands.

See `references/vpn-and-tailscale-coexistence.md` when a VPN client on the host
breaks Tailscale reachability, or when asked to disconnect a VPN and remove it
from autostart (socket activation and the coexistence helper unit both resurrect
it).

See `references/always-on-service-and-tailscale-serve.md` for turning a project
into an always-on systemd service and exposing a loopback-only admin/API over
the tailnet with Tailscale Serve, without rebinding the app's own listen address.

## Disabling a background service for good: mask, not disable

`systemctl disable` only removes the wanted-by symlink; the unit can still be
pulled in as another unit's dependency or by a socket activation, so a sync
agent reappears later. Mask it, kill the running process, and verify the port is
free rather than trusting the unit state:

```bash
systemctl --user stop <unit>; systemctl --user disable <unit>; systemctl --user mask <unit>
pkill -x <binary>; sleep 2; pgrep -a <binary> || echo 'not running'
ss -ltnp | grep <port> || echo 'port free'
```

Report how to reverse it (`unmask` + `enable --now`) and state that data
directories were left untouched — "turn it off" is not "delete my files".

## Report style

Give the conclusion first, then only the readings that support it. Distinguish confirmed findings from plausible but unproven causes; do not give a long command-by-command narrative. Avoid repeated progress messages for routine probes; this user wants the verified outcome, not a running commentary.
