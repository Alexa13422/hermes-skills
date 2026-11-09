# Diagnosing residual VPN policy-routing

A WireGuard-based VPN client (NordVPN's nordlynx, others) installs policy routing to
force traffic through its tunnel. On a messy disconnect it leaves these behind, and
un-marked traffic gets blackholed while occasional packets (those matching a leftover
fwmark rule pointing at `main`) slip through — which makes the box look "mostly online"
and hides the cause.

## What to inspect

```
ip rule show                 # policy rules, lowest pref wins
ip route show table main     # normal routes; default via LAN gw should be here
ip route show table <N>      # the table a suspicious rule points at
ip link show                 # leftover tunnel iface still UP (e.g. nordlynx)
sudo iptables -S             # filter chains (legacy)
sudo iptables -t mangle -S   # fwmark tagging (legacy)
sudo nft list ruleset        # nftables — where modern clients put the killswitch
```

Always check `nft list ruleset` even when `iptables -S` is all-ACCEPT. Modern VPN
clients (current NordVPN) install their killswitch as an nftables table
(`table inet nordvpn`), which is invisible to `iptables -S` — the legacy view looks
clean while nft silently drops all non-tunnel egress. The tell is
`write udp ...:53: operation not permitted` (or any `operation not permitted` on
send) from a daemon: that is a firewall DROP, not a routing hole.

## The signature of residue

- An `ip rule` like `<pref>: from all lookup <N>` where `ip route show table <N>` is EMPTY
  → every packet not caught by an earlier rule is sent to a table with no default route and
  is dropped.
- fwmark rules such as `from all fwmark 0x.../0x... unreachable` / `... lookup default` where
  `default` table doesn't exist → un-marked traffic hits `unreachable`.
- A tunnel interface (`nordlynx`, `wg0`, `nordtun`) still `UP` even though the VPN service is
  `systemctl is-active` = inactive.
- An orphan nftables killswitch table (`table inet nordvpn`, or similar named after the client)
  in `nft list ruleset` while the service is inactive → outbound packets that aren't going
  through the tunnel get `operation not permitted`. iptables can be entirely ACCEPT at the
  same time; the two firewall backends are independent.

## Fix

1. Bring down and delete the orphan interface:
   `sudo ip link set <iface> down; sudo ip link delete <iface>`
2. Delete each orphan rule by its preference number:
   `sudo ip rule del pref <pref>` (repeat for each VPN-added rule).
2b. Delete the orphan nftables killswitch table if present:
   `sudo nft delete table inet nordvpn` (use the actual table name from `nft list ruleset`).
3. Verify: after cleanup `ip rule show` should be the kernel defaults (`local` / `main` /
   `default`) plus any legitimate mesh-VPN rules (Tailscale adds e.g.
   `not from all fwmark 0xe1f1 lookup 205` and `from all lookup main suppress_prefixlength 0`
   — those are fine, leave them).
4. Re-test the failing service (`tailscale netcheck`, `curl -4`, etc.).

These deletions are runtime-only; they do not survive reboot unless the VPN client re-adds
them on boot. If the box reboots and breaks again, disable/uninstall the VPN client's
autostart rather than re-deleting rules each time.
