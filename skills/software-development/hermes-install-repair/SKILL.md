---
name: hermes-install-repair
description: "Repair a broken Hermes install on Windows."
version: 1.0.0
author: hermes-curator
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, electron, installer, windows, troubleshooting, bootstrap]
    related_skills: [inspecting-hermes-desktop-dom, systematic-debugging]
---

# Repairing a broken Hermes install (Windows)

## When to Use

The Hermes desktop app won't start, shows a blank/white window or an "INSTALL DIDN'T FINISH"
screen; `Hermes-Setup.exe` or the bootstrap installer dies partway; the launcher in
`~/AppData/Local/hermes/bin` is stale or refuses to be replaced.

## Procedure

1. **Read the installer log before touching the build tree:**
   `~/AppData/Local/hermes/logs/bootstrap-installer.log`. It is stage-structured
   (`stage=repository`, `stage=python`, `stage=webui`, `stage=desktop`, `stage=products`);
   grep `-nE 'ERROR|FAILED|\[X\]|stage='` and read the LAST stage's tail. Also check
   `logs/desktop.log`, `logs/gui.log`, `logs/errors.log`.
2. **Prefer re-running the official installer over hand-patching the build tree.** A partially
   built `apps/desktop/release/win-unpacked` has many independent ways to be incomplete
   (missing `icudtl.dat`, `d3dcompiler_47.dll`, `dxil.dll`, missing
   `app.asar.unpacked/dist/electron-main.mjs`, a truncated `apps/desktop/package.json`);
   fixing them one error dialog at a time costs far more time than one full rebuild. Run the
   installer with the CLI's own env stripped:
   `env -u NODE_OPTIONS -u HERMES_SESSION_ID -u _HERMES_GATEWAY -u HERMES_QUIET -u HERMES_INTERACTIVE ./Hermes-Setup.exe`
   in the background, then watch the log with short `sleep` + `tail -n N | cut -c1-200` — a single
   long foreground wait hits the terminal tool's timeout, and the npm-install/desktop-build stage
   alone runs 10+ minutes.
3. **Repair a locally corrupted tracked file from git, not by editing it:**
   `git show HEAD:apps/desktop/package.json > apps/desktop/package.json`. Plain
   `git checkout -- <path>` can fail on this tree; `git show` always works.
4. **After the build, verify by timestamp** that `release/win-unpacked/Hermes.exe` and
   `resources/` were actually rewritten by this run before concluding the rebuild succeeded.

## Known blockers

- **`fatal: remote helper 'https' aborted session` / stage=repository**: the bundled portable git
  under `~/AppData/Local/hermes/tools/git-*/mingw64/libexec/git-core` can ship without
  `git-remote-http.exe` / `git-remote-https.exe`, so every fetch dies. Fix by copying
  `git-remote-ftp.exe` to both names — the remote helpers are one multiplexed binary that
  selects the protocol from `argv[0]`. Confirm with `git ls-remote --heads origin main` using
  that git on PATH.
- **stage=products "launcher staging failed"**: the installer cannot overwrite
  `~/AppData/Local/hermes/bin/hermes.exe` because a *running Hermes CLI session* — very likely
  the one you are working in — holds the image open. Windows refuses both rename and copy;
  `MoveFileExW` returns error 32 (`ERROR_SHARING_VIOLATION`) and PowerShell `Move-Item` reports
  the file in use. No in-session trick removes a lock on your own executable: identify the owning
  PID (`Get-CimInstance Win32_Process -Filter "Name='hermes.exe'"`), confirm it is the current
  session, and tell the user to exit it and re-run the installer / "Retry install". Do not report
  the install as complete while this stage is unfinished.

## Diagnosing a GUI that shows nothing useful

Electron startup failures surface in a native dialog, not in stdout, so the log looks clean while
the app is dead. Capture the screen and read it:
PowerShell `[System.Windows.Forms.Screen]::PrimaryScreen.Bounds` +
`Graphics.CopyFromScreen` → PNG, then `vision_analyze` the file. For a single window use ctypes
`EnumWindows`/`PrintWindow` to a BMP and convert with `ffmpeg`. When shelling out to `tasklist`
from Python, use `capture_output=True` and `.stdout.decode('utf-8','replace')` — `text=True`
raises on the console codepage.

Launch the app from a cleaned environment (`env -u NODE_OPTIONS -u HERMES_SESSION_ID
-u _HERMES_GATEWAY -u HERMES_QUIET -u HERMES_INTERACTIVE`): variables inherited from the CLI
session change how the Electron main process boots.

Before relaunching, kill only the stale GUI processes and never the current session:
`Get-Process Hermes | Where-Object {$_.Path -like '*win-unpacked*'} | Stop-Process -Force`.

## Reporting

The user wants a compact Ukrainian report: what was actually broken (root cause per stage), what
is now verified working, and the one concrete action left for them — not a narrative of attempts.
