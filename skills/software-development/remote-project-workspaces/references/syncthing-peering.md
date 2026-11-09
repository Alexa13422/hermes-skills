# Syncthing peering and disconnect diagnosis

For "Syncthing says disconnected" between two machines (e.g. Linux host and Windows PC).
Drive everything through the REST API — never ask the user to open the GUI.

## Setup facts to establish first

- Config dir differs by version: newer builds use `~/.local/state/syncthing`, older
  `~/.config/syncthing`. Probe both; the one containing `config.xml` is live.
- The API key is in `config.xml`: `grep -oP '(?<=<apikey>)[^<]+' config.xml`. Export it
  once and reuse — every call needs `-H "X-API-Key: $APIKEY"` against
  `http://127.0.0.1:8384`.
- Service unit is commonly `syncthing@<user>` (system) or a `--user` unit. Check both
  with `systemctl is-active`; a `--user` unit shows `inactive` while the system one runs,
  which is not a fault.

## Diagnose in this order

1. `journalctl -u syncthing@<user> --since "-5min"` and grep for the peer name and
   `reject`. **Read the log before touching config.** A log line like
   `rejected: unknown device` means the peer is reaching you and being refused at the
   identity layer — no amount of address, discovery, relay, or firewall tuning fixes
   that, and changing them buries the signal.
2. `/rest/system/status` → `myID`, discovery errors. `/rest/config/devices` and
   `/rest/config/folders` → who is known and which folders are shared with whom.
3. `/rest/system/connections` → per-device `connected`, `address`, `type`.
4. Reachability of the peer's sync port: `timeout 5 bash -c 'cat </dev/null >/dev/tcp/<ip>/22000'`
   over both LAN and Tailscale addresses.

## Root cause: peer reinstalled and has a new device ID

A reinstalled or config-reset Syncthing generates a **new** device ID. The old entry
stays in your config forever looking merely "disconnected", so the symptom reads as a
network problem while the peer is actually being rejected by identity. Fix:

1. Get the new ID from the rejection log line (it prints the full device ID).
2. Add it: `POST /rest/config/devices` with `{"deviceID":...,"name":...,"addresses":[...],"compression":"metadata","introducer":false,"paused":false}`.
3. **Re-share every folder with the new ID.** Adding the device alone transfers nothing;
   folder membership is keyed on device ID, so the new peer connects and syncs zero files.
   `GET /rest/config/folders/<id>`, append to `devices[]`, `PUT` the whole object back.
4. Delete the stale entry with `DELETE /rest/config/devices/<oldID>` only after the new
   one connects, so you keep a rollback path.

## Address and discovery hygiene

- Put the stable overlay address first in a device's `addresses`, then the LAN address,
  then `"dynamic"`: `["tcp://<tailscale-ip>:22000","tcp://<lan-ip>:22000","dynamic"]`.
  Tailscale keeps working when the machines are on different networks; LAN is the fast path.
- `PATCH /rest/config/options` with `{"globalAnnounceEnabled":true,"relaysEnabled":true,"natEnabled":true}`
  when only local discovery was on — without global announce the peers can only find each
  other on the same subnet.
- Back up `config.xml` before structural edits; API writes take effect immediately.
- A router without NAT-PMP/UPnP is a non-issue when LAN plus an overlay network already
  provide a path. Do not report it as a problem to solve.

## Verify before reporting success

`connected: true` is not synchronization. Confirm all three:

- `/rest/db/status?folder=<id>` → `state: idle`, `needFiles: 0`, `errors: 0`,
  `pullErrors: 0`. `state: scanning` means wait and re-poll.
- `/rest/db/completion?folder=<id>&device=<peerID>` → `completion: 100`, `needItems: 0`.
  This is the only call that proves the *peer* is current, not just reachable.
- `systemctl is-enabled` → the unit survives reboot.

Report file count, total size, completion percent and error count — not the command log.
