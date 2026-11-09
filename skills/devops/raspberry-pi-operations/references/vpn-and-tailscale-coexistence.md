# Coexisting VPN and Tailscale on a Linux host

A consumer VPN client and Tailscale both want to own routing, firewall and DNS.
By default the VPN wins and the Tailscale mesh goes dark — which looks like
"the Pi went offline" from every other device.

## Make them coexist (NordVPN CLI)

Allowlist the whole Tailscale CGNAT range, not individual peer IPs — peer
addresses change and a per-IP rule silently stops covering a new device:

```bash
nordvpn allowlist add subnet 100.64.0.0/10
nordvpn allowlist add port 41641   # Tailscale WireGuard
nordvpn allowlist add port 22      # SSH
# plus any local service port you reach over the mesh
nordvpn settings
```

A private LAN subnet may be refused while LAN Discovery is enabled
("not available while local network discovery is turned on"). That is not a
failure to work around: LAN Discovery already permits the local network, and an
`ip rule` for `192.168.0.0/16 lookup main` should be present.

## Verify with the VPN CONNECTED, never from settings alone

Settings output only proves intent. Connect, then prove the mesh survives:

```bash
nordvpn connect
tailscale ping -c 2 <peer-tailscale-ip>     # expect a pong
ip route get <peer-tailscale-ip>            # expect dev tailscale0
curl -s ipinfo.io/json                      # expect the VPN exit country
grep nameserver /etc/resolv.conf            # expect 100.100.100.100 if MagicDNS
sudo nft list table inet nordvpn | grep -E '100\.64|allowlist'
```

A `pong ... via 192.168.x.x` line proves the peer is reached directly rather
than being blackholed. Seeing the allowlist range inside `@allowlist_subnets`
with an `accept` rule confirms the config reached nftables, not just the CLI's
own state.

## The output chain drops Tailscale's marked packets even with a correct allowlist

The allowlist above covers mesh *peer* traffic (100.64.0.0/10). It does NOT
cover tailscaled's traffic to the public control plane and DERP relays, which
leaves the daemon unable to fetch a network map — peers show `offline` from every
other device while the local `tailscale0` interface still looks up.

The mechanism: NordVPN's `table inet nordvpn` installs an output chain with
`policy drop`, and tailscaled marks its own sockets with `fwmark 0x80000`. That
mark matches none of the accept rules, so the packets are dropped silently —
no log, no error, just a stalled daemon reporting "hasn't received a network map".

Confirm it is this rather than DNS or an auth problem:

```bash
sudo tailscale netcheck            # UDP: false + "Nearest DERP: unknown" = blocked egress
ip route get 1.1.1.1 mark 0x80000  # should leave via the LAN gateway, not nordlynx
sudo nft list chain inet nordvpn output | head
```

Fix by letting the marked packets out and setting the conntrack mark, so replies
match the table's own "VPN transport continuation" rule:

```bash
sudo nft insert rule inet nordvpn output \
  meta mark and 0xff0000 == 0x80000 ct mark set 0x0000e1f1 accept \
  comment '"tailscale SO_MARK bypass"'
sudo nft insert rule inet nordvpn input \
  meta l4proto udp udp dport 41641 accept \
  comment '"tailscale wireguard in"'
sudo tailscale set --accept-dns=false   # stop Tailscale rewriting resolv.conf under the VPN
```

Then re-check `tailscale netcheck` for `UDP: true` and a named nearest DERP, and
`tailscale ping` a peer for a real `pong`.

**Persist it: the VPN recreates the table on every reconnect**, so a hand-added
rule survives only until the next connect and the mesh dies again days later.
Install an idempotent script guarded by a `grep` for its own rule comment, plus a
oneshot unit ordered `After=nordvpnd.service tailscaled.service` and enabled for
`multi-user.target`. Run the script a second time and assert the rule count is
still 1 before claiming it is idempotent.

## Tearing the VPN down for good (only when the user asks for it)

`nordvpn disconnect` is the whole answer for "turn it off now" — it drops the
`nordlynx` interface, and the client removes its own nftables table and restores
`/etc/resolv.conf`. State that plain command when reporting, since the user may
want to repeat it by hand later.

Autostart removal is a separate, standing change and needs all four of these;
any one left behind brings the VPN back at next boot:

```bash
sudo systemctl disable --now nordvpnd.socket    # socket activation alone restarts the daemon
sudo systemctl disable --now nordvpnd.service
sudo systemctl mask nordvpnd-killswitch.service # 'static' unit: disable is refused, only mask works
sudo systemctl disable --now tailscale-nord-bypass.service
```

**The coexistence helper from this very reference is a resurrection vector.** The
oneshot bypass unit is ordered `After=nordvpnd.service` *and* declares
`Wants=nordvpnd.service`, so systemd starts the VPN daemon to satisfy that want —
the VPN comes back despite every `disable` above. Before declaring a daemon gone,
enumerate what still pulls it and read each hit rather than trusting unit state:

```bash
grep -rlE '<daemon>' /etc/systemd/system/
systemctl list-dependencies --reverse <daemon>.service
systemctl list-unit-files | grep -iE '<daemon>'   # catches .socket and masked/static units
```

Verify by effect, not by `is-enabled`: `nft list tables` has no `inet nordvpn`,
`ip -brief addr` has no `nordlynx`, `/etc/resolv.conf` is off the VPN resolvers,
the public IP changed, and `tailscale status` still reaches peers. Numbered ip
rules in the 5200s belong to Tailscale and correctly stay. Report the one-line
reversal (`enable --now` the socket and service).

## Pitfalls

- **Do not accept the user's attribution of which component broke the mesh.**
  When they name the app they suspect, still check `nft list tables`, `ip rule`
  and the VPN client's own status first: a VPN connected for days is the common
  cause, and disabling the suspected app proves nothing because it was never in
  the path.
- **Kill Switch is the usual culprit, but confirm before changing anything.**
  Read `nordvpn settings` first; if it is already disabled, the breakage is
  routing/allowlist, and disabling more protections fixes nothing.
- **Auto-connect off means the allowlist is untested across reboot.** Say so
  rather than promising persistence you have not observed.
- **A VPN daemon running while its status says Disconnected still installs its
  nftables table and ip rules.** Judge by `nft list tables` and `ip rule show`,
  not by the status line.
- **Leftover state outlives an uninstall.** Look for `table inet nordvpn`,
  numbered ip rules in the 5200s, a `nordlynx` interface, and rewritten
  `/etc/resolv.conf` when mesh connectivity misbehaves after removal.
- **Never disable the VPN client's autostart to unblock Tailscale, even as a
  quick fix, without asking first.** A one-off `nordvpn disconnect` to restore
  the mesh for the current session is reversible and fine; flipping
  `systemctl disable/mask nordvpnd` is a standing change to how the user's
  machine boots and is exactly the kind of action they may have set up
  deliberately for an unrelated reason. If disconnecting restores Tailscale,
  report that and stop — do not also touch the daemon's enablement state. Only
  when the user explicitly asks to remove it from autostart, follow "Tearing the
  VPN down for good" above. If an agent did this uninvited and the user says to
  leave the VPN alone, immediately `systemctl enable nordvpnd` (or whatever
  obscure daemon) again and remember: future autostart/killswitch/config changes
  on this host need explicit permission even when they would fix a real
  connectivity problem.
