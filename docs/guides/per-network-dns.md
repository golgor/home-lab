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

[DHCPv4]
UseDNS=no
RouteMetric=600

[IPv6AcceptRA]
UseDNS=no
RouteMetric=600
```

Replace `<your-home-ssid>` with the exact network name and `10.0.0.110` with
the PiHole service IP.

## Apply

```bash
sudo networkctl reload
```

## Verify

```bash
resolvectl status wlan0
```

`Current DNS Server` should show the PiHole IP when connected to the home
network, and revert to the network-provided DNS on any other network.
