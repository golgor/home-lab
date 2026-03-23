# Per-Network DNS on Omarchy

How to configure DNS per Wi-Fi network on Omarchy, so the local PiHole is used
at home but other networks fall back to their own DNS automatically.

## Background

Omarchy uses `iwd` for Wi-Fi and `systemd-networkd` for network configuration.
The generic `/etc/systemd/network/20-wlan.network` applies to all Wi-Fi
connections but does not set a DNS server (it ignores the one from DHCP via
`UseDNS=no`).

Since systemd v255, `.network` files support `SSID=` in the `[Match]` section,
making it possible to apply a different configuration per Wi-Fi network without
any scripts or hooks.

## Create a home-network profile

Create `/etc/systemd/network/10-wlan-home.network` (the lower number gives it
higher priority over the generic `20-wlan.network`):

```ini
[Match]
Name=wl*
SSID=<your-home-ssid>

[Network]
DHCP=yes
MulticastDNS=yes
DNS=10.0.0.110
Domains=~.

[DHCPv4]
UseDNS=no
RouteMetric=600

[IPv6AcceptRA]
UseDNS=no
RouteMetric=600

[DHCPv6]
UseDNS=no
```

Replace `<your-home-ssid>` with the exact network name and `10.0.0.110` with
the PiHole service IP.

### Why `Domains=~.` and three `UseDNS=no` entries

`Domains=~.` tells systemd-resolved to route **all** DNS queries through PiHole,
not just queries for `*.neustrom.net` subdomains. Without it, apex domain queries
(e.g. `neustrom.net` itself) fall through to the global DNS which has no record
for local addresses.

The three `UseDNS=no` entries prevent the router from injecting its own DNS
server via DHCPv4, DHCPv6, or IPv6 Router Advertisements. Without all three,
the router's IPv6 link-local address gets added to the DNS server list and
systemd-resolved may select it over PiHole, breaking local resolution entirely.

## Apply

```bash
sudo networkctl reload
```

## Verify

```bash
resolvectl status wlan0
```

The output should show:

- `Current DNS Server: 10.0.0.110` — and only that, no router IPv6 address
- `DNS Domain: ~.`
- `Default Route: yes`

`Current DNS Server` reverts to the network-provided DNS on any other network.
