---
name: windows-background-process-diagnosis
description: Trace a Windows flashing console/popup or slow boot to its cause.
---

# Diagnosing mystery recurring processes/windows and slow boot on Windows

When the user reports something flashing/popping up periodically (a console
window, an error dialog), or that the PC takes a long time to restart/become
usable, the cause is almost always a Scheduled Task, a Run-key autostart
entry, or startup bloat — not an AI agent, not malware by default. Check the
mundane, deterministic sources first.

## Procedure
1. Dump all scheduled tasks to a file in `$TMPDIR` rather than printing inline
 — `schtasks /query /fo LIST /v` is tens of thousands of lines, almost all
 stock Windows/Microsoft tasks:
   `schtasks /query /fo LIST /v > "$TMPDIR/tasks.txt"`
2. Grep that file for the shape of the real cause instead of reading it:
   - tasks whose `Task To Run` is `cmd.exe`/`powershell.exe` WITHOUT
     `-WindowStyle Hidden` or `-NonInteractive` — these are exactly the ones
     that flash a visible console.
   - tasks with a non-zero `Last Result` on a `Daily`/frequent `Schedule
     Type` — a task that fires on a schedule matching the user's observed
     timing AND errors every run is the strongest signal.
   - the task's `Author` being the user's own account (not `N/A`/Microsoft)
     narrows it to something they or prior tooling set up.
3. Also check autostart entries, since not every popup is a scheduled task:
   - `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run"` and
     the `HKLM` and `HKLM\...\WOW6432Node` equivalents
   - the Startup folder: `ls "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup"`
4. Once a suspect task is named, re-query just that one for the full command
 line instead of re-scanning the giant dump: `schtasks /query /tn "<name>"
 /fo LIST /v`.
5. Reproduce by hand: `cd` to the script's directory and run the exact
 interpreter/script the task invokes (e.g. the `.bat`'s `python.exe
 script.py` line) directly in the terminal. This surfaces the real
 traceback/error that the flashing window hides, instead of guessing from
 the task metadata alone.
6. Present the fix as a choice, don't just disable things: either fix the
 underlying cause (missing `.env`/config the script depends on, wrong
 working directory, etc.) or disable the task if the user no longer wants
 it — `schtasks /change /tn "<name>" /disable`. Ask which before acting,
 since a recurring task was usually set up on purpose at some point.

## Diagnosing a slow restart (distinct from a flashing popup)
1. First separate "OS boot is slow" from "login is slow because of what
 loads after": compare System-log `Kernel-General` events 13 (shutdown)
 and 12 (boot complete) timestamps — `Get-WinEvent -FilterHashtable
 @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-General';
 Id=12,13}` needs no elevation and gives the actual shutdown→boot
 duration. A few minutes here, especially around a Windows-Update
 "Service pack (Planned)" restart (check `Id=1074` in the System log for
 the reason string), is normal and not the bug.
2. The real complaint is usually the minutes AFTER boot while autostart
 items load. List them with `Get-CimInstance Win32_StartupCommand |
 Select Name, Command, Location` — flag heavy/non-essential entries
 (game launchers, Docker Desktop, GPU/peripheral utility trays, updater
 checkers) as the fix target, not the boot sequence itself.
3. Removing a `HKCU:\...\Run` entry works directly with
 `Remove-ItemProperty`. A `HKLM:\...\Run` entry needs admin and
 `Start-Process powershell -Verb RunAs` from this automated terminal gets
 auto-cancelled (no interactive UAC prompt reaches the user) — don't
 retry elevation in a loop. Do the HKCU ones yourself, then tell the user
 to disable the remaining HKLM-rooted ones manually via Task Manager →
 Startup tab (right-click → Disable), which elevates through the normal
 UAC flow they can approve.

## Electron desktop apps that launch then disappear
1. For Electron apps such as VS Code or Docker Desktop, distinguish a dead backend from a broken UI: inspect the app's processes, then test its CLI/API if available. A working backend/API with no visible window narrows the failure to the Electron frontend.
2. Launch the executable from `cmd.exe /c start "<title>" "C:\...\App.exe"` rather than invoking it directly from MSYS bash; paths with spaces otherwise split and create a false launch failure.
3. If the app prints `Invalid file descriptor to ICU data received` and exits before loading, treat the install as damaged. Update/reinstall through the official package manager, preserving the user data directory; then launch with `--disable-extensions` and verify that the expected child processes remain alive.
4. Do not infer an Electron GUI failure from a backend idle shutdown alone. Some desktop apps deliberately stop their engine after an inactivity timer and restart it on demand.

## Compatibility Assistant security popups
1. When **Program Compatibility Assistant** says a module is blocked from
   loading into Local Security Authority (LSA), identify the DLL path before
   changing any security setting. A third-party DLL being blocked is normally
   a successful LSA-protection decision, not an LSA failure.
2. Map the DLL to its owning installed product, then offer the safe choices:
   update that product, uninstall it if unused, or suppress the informational
   popup. Do not disable LSA protection just to accommodate an obsolete
   module; that weakens credential protection system-wide.

## PowerShell invocation from this bash tool
- Inline `powershell.exe -Command "...$_..."` through this bash tool is
 fragile: bash/MSYS quoting eats `$` and multi-statement `;`-joined
 one-liners before PowerShell sees them ("empty pipe element", "missing
 file specification" errors are this, not a real PowerShell bug). Write
 the script to a `.ps1` file in `$TMPDIR`/scratch with the `Write` tool,
 then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
 "<path>.ps1"`.
- Protected ETW channels like
 `Microsoft-Windows-Diagnostics-Performance/Operational` throw
 `UnauthorizedAccessException` from a non-elevated `Get-WinEvent` even
 with `-ErrorAction SilentlyContinue` on the whole pipeline (the access
 check happens before the catch applies at the call site) — don't loop
 retrying filters on them; fall back to the unprotected `System`/`Application`
 logs (`Kernel-General`, `Kernel-Power` id 41, id 6008, id 1074) which
 answer the same boot/shutdown questions without elevation.

## Pitfalls
- Don't assume a periodic popup is caused by an AI agent, cron job, or
 malware — `cronjob_manage(action='list')` only shows Hermes-scheduled jobs,
 and most mystery windows trace back to the user's own old scheduled task or
 a bundled vendor updater. Rule it out with the scan above before escalating
 the user's worry.
- `grep`/`Grep` tool content search can fail on huge multi-thousand-line
 native dumps piped through `/tmp` paths on this host; redirect to
 `$TMPDIR/<file>` and use plain shell `grep`/`awk` on it, or read it back
 with the `Read` tool using the exact saved-log path the terminal result
 reports (its own `/tmp/...` alias and the real Windows cache path can
 diverge — use whichever path the tool result actually printed).
