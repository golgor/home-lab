---
status: accepted
date: 2026-10-11
---

# OpenTofu for all infrastructure, replacing Pulumi, and ArgoCD for apps

We decided to split the code by layer, the same way Robert's work setup does. OpenTofu declares everything outside
the cluster: the Proxmox VMs through the `bpg/proxmox` provider and the Talos machine config. ArgoCD syncs every
Kubernetes manifest from git, including the databases and roles, which CloudNativePG now owns (see
[ADR 0007](0007-cloudnativepg-in-cluster-replacing-host-postgres.md)). Pulumi, which manages the Postgres roles on the
Pi today, was an experiment and is retired. A rebuild is one OpenTofu run followed by ArgoCD reconciling the apps.

## Considered options

- Keep Pulumi next to OpenTofu, or move everything to Pulumi. Pulumi has no first-class, maintained Proxmox support to
  match `bpg/proxmox` for OpenTofu, and two infrastructure tools mean two state stores, two credential paths and two
  sets of habits. One tool wins.
- Manage the VMs by hand. Workable for a few changes a year, but then a rebuild depends on notes instead of code.
- Ansible for VMs and Talos. Ansible fits OS configuration, and Talos has no OS to configure that way.

## State

- OpenTofu state lives in an S3-compatible backend on Cloudflare R2.
- OpenTofu's native state encryption encrypts it, with the key stored in the "Neustrom" secrets store.
- Local state was rejected because a lost laptop would lose it, which is the problem Pulumi has today.
- S3 or MinIO on the Proxmox host was rejected because state that describes the host must not live on it.
- The encryption matters because the Talos provider keeps the cluster's secrets in state.

## Consequences

- Robert runs `tofu apply`. It is a human gate.
- Agents write OpenTofu code and open pull requests. `tofu plan` does not run in CI for now. Proxmox is LAN-only, so a
  plan in CI would need something on the home network and credentials Robert has not decided on.
- The Talos machine config lives in git as templates or patches with no secrets in them. The secrets bundle lives in
  the secrets store.
- `talosconfig` and kubeconfig never go into git. A mise task pulls the secrets bundle and writes both files locally,
  so a lost laptop costs nothing.
- The Pulumi project under `infrastructure/`, its local state and the `docs/guides/pulumi/` pages go away with the
  host-level Postgres they manage.
- Choosing between the `siderolabs/talos` provider and `talhelper` is still open.
- The Proxmox host itself stays outside OpenTofu. See [ADR 0003](0003-proxmox-host-talos-vm-separate-ha-vm.md).
