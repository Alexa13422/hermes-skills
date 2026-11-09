---
name: browser-real-profile-login
description: Use when a site needs the user's own login; no connector.
---

# Accessing a site via the user's real logged-in browser

When a task needs content only visible to the user's logged-in account, and no
hosted connector or MCP exists for that app, drive the user's own Chromium
profile with `BrowserExec(local=true)` instead of the cloud browser — logins/
cookies live there.

## Procedure
1. Check `ManageConnections(action='status')` and `ToolSearch` for a connector
 or MCP server first — only fall back to the local real browser if neither
 exists for the target app.
2. Before touching the user's browser or any login flow, confirm with the
 user: which browser/profile, which specific content to look at, and what to
 do with what's found (summarize vs. just counts). Treat chat/DM access as
 sensitive — always confirm scope before reading someone's private messages.
3. Call `BrowserExec(code=..., local=true)`. If it errors with "profile is
 locked" (the real browser process is running and holds the profile files),
 get the user's explicit OK to close it (it drops unsaved tabs), then run
 `hermes browser close-profile`.
4. `close-profile` only closes the window it can see — some browsers (Brave
 observed) auto-relaunch themselves (background/tray mode or an updater
 re-spawning). Check with `tasklist /fi "imagename eq <browser>.exe"`; if
 processes reappear, force-kill directly: `taskkill /IM brave.exe /T /F`
 (also kill `*Update.exe` helpers), then immediately retry the BrowserExec
 call before anything else relaunches it.
5. After the profile copies successfully, the target site may still show its
 login form (cookies/session state don't always carry over from the copy).
 Do NOT type the user's password or credentials yourself under any
 circumstances. Ask the user to log in themselves in that same automated
 tab and say when done, or stop and let them decide how to proceed — never
 substitute a guessed workflow for a real login.
