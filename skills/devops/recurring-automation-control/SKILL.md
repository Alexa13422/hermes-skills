---
name: recurring-automation-control
description: "Use when stopping or auditing a recurring job or bot."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cron, systemd, scheduler, notifications, automation, audit]
    related_skills: [remote-project-workspaces, raspberry-pi-operations]
---

# Recurring automation control

## When to Use

For "turn off that job", "stop the bot that messages me", "why does this keep
firing", "pause the monitor" — anything about a *repeating* action rather than a
one-shot task. Also for auditing what recurring automation exists across this
host and the user's other machines.

## Core rule: a paused job is not a stopped action

The same recurring action is frequently wired through **two independent
schedulers**, and disabling one leaves the other firing. Never report an action
stopped after touching a single layer. Enumerate all of these before concluding:

```bash
cronjob_manage(action='list')                       # agent-level jobs
systemctl --user list-timers --all --no-pager       # user timers (ALSO shows inactive)
systemctl list-timers --all --no-pager              # system timers
crontab -l; ls /etc/cron.d/                         # classic cron
```

On Windows (over SSH — see `remote-project-workspaces` for the alias and
quoting rules):

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match '<keyword>' } |
  Select-Object TaskName, State
```

An agent-level job showing `paused` while a `systemd` timer runs the same script
is the archetypal miss: the cron entry is a wrapper, the timer invokes the shell
script directly and never consults it.

## Procedure

1. **Enumerate every scheduler** per the block above, on every host that could
   run the action. A job that notifies a phone can be scheduled on a different
   machine than the one you are logged into — if the payload script lives in a
   synced directory (a vault, OneDrive, Syncthing share), assume the scheduler
   is on the *other* machine until proven otherwise. `.bat`/`.ps1` launchers
   sitting next to a Python script are the tell that a Windows Task Scheduler
   entry drives it.
2. **Find the payload by content, not by name.** Grep the literal text the user
   quoted across likely roots; the scheduler entry rarely mentions it:
   ```bash
   search_files '<distinctive phrase from the message>' --target content --path ~
   ```
   This lands on the data file or sender script, and the scheduler is then found
   by grepping for *that filename*.
3. **Stop and disable, in that order**, so the job neither runs now nor returns
   after reboot:
   ```bash
   systemctl --user stop <unit>.timer <unit>.service
   systemctl --user disable <unit>.timer
   ```
   `systemctl --user is-active <unit>.timer` and `is-enabled` are the proof.
   `disable` alone leaves a running timer live until reboot; `stop` alone lets
   it come back. For `oneshot` services a `failed`/`inactive` state after stop is
   expected, not an error to chase.
   Windows: `schtasks /change /tn "<name>" /disable`, then confirm
   `Status: Disabled` and `Next Run Time: N/A`.
4. **Verify the sender before claiming you disabled the thing that messaged the
   user.** Disabling a plausible candidate is not evidence it was the source.
   Check the scheduler's own last-run record and the message store:
   - `schtasks /query /tn "<name>" /fo LIST /v` — `Last Run Time` and
     `Last Result` (nonzero = it errored, so it delivered nothing).
   - the agent message database, for an actual inbound message carrying the text.
   If the only record of the text is the user's **own** message quoting it, no
   live sender exists — say so plainly instead of accepting credit for a fix.
   An "already disabled" response from the scheduler is a strong hint you are
   looking at the wrong source.
5. Report: what was actually firing, what is now stopped and disabled with the
   verified state, and anything you disabled defensively that was already dead.

## Pitfalls

- Query `list-timers` with `--all`; the default view hides inactive units, so a
  timer you just stopped or one that failed at boot silently vanishes from the
  audit and reads as "not present".
- Do not delete units, jobs, or scripts when asked to turn something off. The
  word used is nearly always "pause"/"for now" and the automation is expected
  back; disable preserves the config and the user's work.
- `sqlite3` and `atq` are not installed everywhere. Read SQLite state through
  Python (`sqlite3` module, `mode=ro` URI) rather than reporting the missing
  binary as a dead end.
- Two agent gateways pointed at the same chat produce duplicated or crossed
  replies. While auditing schedulers, note any second gateway process you find
  on another host and ask before killing it — it may be the user's main one.
