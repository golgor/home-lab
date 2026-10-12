---
status: accepted
date: 2026-10-11
---

# Proxmox host with a Talos cluster VM and a separate Home Assistant VM

The Raspberry Pi 5 lacks memory and disk redundancy, and Home Assistant needs USB and radio hardware, which fits
poorly in Kubernetes. We decided to replace the Pi with an x86-64 mini PC running Proxmox VE 9 on a two-disk ZFS
mirror, with one VM running Talos as a single-node cluster and a separate VM running Home Assistant OS. The cluster
ingress routes to the Home Assistant VM, so the tunnel into the cluster is the only public way into either.

## Considered options

- k3s on bare metal on the mini PC, as on the Pi today. Simpler, but Home Assistant would then share the host with the
  cluster, and there are no VM snapshots before upgrades.
- k3s in a VM. Robert knows k3s, but it keeps a general-purpose OS with SSH to harden and patch. Talos has no SSH and
  no shell, and the whole OS is an API and a machine config, which suits agents and shrinks what can be attacked.
- Home Assistant inside the cluster. It depends on hardware passthrough and host networking, so it was rejected.
- Home Assistant Container in its own VM. Supported, but it has no apps, so the Matter server and Thread would have to
  be run by hand, and its backups cover config only.
- Moving the Pi's disk over as it is. Rejected in favour of a fresh build from git, which also proves the repo really
  describes the lab.

## Home Assistant VM

Details and sources are in [research/home-assistant.md](../research/home-assistant.md).

- Home Assistant OS, declared with `bpg/proxmox`: UEFI (OVMF) with secure boot off, machine type `q35`, bridged onto
  the LAN on `vmbr0`. IPv6 is enabled on the LAN because Matter needs it.
- A fresh start with no restore from an earlier install, and no Home Assistant Cloud.
- The recorder stays on the default SQLite, which Home Assistant recommends. That keeps Home Assistant independent of
  the cluster, and long-term statistics are kept regardless. A time-series store in the cluster, such as InfluxDB or
  VictoriaMetrics, may come later as a secondary copy of history.
- Home Assistant is configured in its UI. Backups manage it, not GitOps. Native backups go to Cloudflare R2 through
  the official integration, and Proxmox backs up the whole VM nightly. The backup emergency kit is kept in Bitwarden.
- The Philips Hue Bridge stays, through Home Assistant's local Hue integration rather than Matter. There is no Zigbee
  for now.
- Matter runs through the Home Assistant OS Matter server app. A Thread radio, such as a combined Zigbee and Thread
  USB stick, is an optional purchase once a Thread device arrives, so the VM keeps USB passthrough ready.
- Traffic reaches it as tunnel, Traefik, then a Service with an EndpointSlice pointing at the VM's IP. ExternalName is
  not used because it takes a hostname. Home Assistant trusts the Talos VM's IP as its proxy.
- Login is `hass-oidc-auth` against Authentik with no proxy-level auth in front. See
  [ADR 0001](0001-tunnel-and-authentik-for-household-admin-lan-only.md).

## Consequences

- The host is installed by hand once from a documented checklist. Host changes are a human gate, and only the VMs are
  code. See [ADR 0004](0004-opentofu-for-infrastructure-replacing-pulumi-argocd-for-apps.md).
- The `bpg/proxmox` OpenTofu provider targets Proxmox VE 9, so the host runs version 9.
- The ZFS mirror survives a failed disk and repairs silent corruption during scrubs. It copies deletions and ransomware
  just as faithfully, so it is not a backup.
- Talos removes Ansible for the cluster, and Home Assistant OS removes it for the Home Assistant VM. Ansible stays
  only for the host, if needed at all.
- Onboarding, integrations, HACS, the OIDC setup and the proxy settings in Home Assistant are manual steps, so they
  are owner:robert work.
- Talos does not ship the Traefik and ServiceLB that k3s bundles, so the ingress and load balancer setup has to be
  chosen again.
- All migration work is blocked until the mini PC is bought.
