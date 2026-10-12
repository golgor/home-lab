---
status: accepted
date: 2026-10-11
---

# CloudNativePG in the cluster, replacing host-level Postgres

Today PostgreSQL 17 runs on the Pi's host OS, configured by Ansible, listening on the LAN, with roles managed by
Pulumi. On the new host there is no general-purpose OS to put it on. We decided to run app databases with
CloudNativePG (CNPG) inside the Talos cluster. Databases and roles are manifests that ArgoCD syncs, and backups go to
Cloudflare R2 through the Barman Cloud Plugin.

## Considered options

- A dedicated Postgres VM. Independent of the cluster, but it is one more OS to patch and harden, with its own backup
  tooling and its own OpenTofu or Ansible code.
- Keep Postgres outside the cluster and manage roles with the OpenTofu `cyrilgdn/postgresql` provider. Role passwords
  would sit in OpenTofu state, and every plan would need network access to the database.
- A plain StatefulSet or a single-app Helm chart per database. Less to install, but no managed roles, scheduled
  backups or point-in-time recovery, and each app would need its own backup setup.

## Consequences

- Apps and their databases share the cluster's fate. That is acceptable because the apps run in the cluster anyway.
  Home Assistant keeps SQLite precisely so that it does not depend on the cluster.
- Agents declare databases and roles in manifests and never see passwords. CNPG generates app credentials as Secrets
  in the cluster. The R2 credentials for backups come through ESO.
- Backups use the Barman Cloud Plugin with an `ObjectStore` resource. The in-tree `barmanObjectStore` field is
  deprecated and is removed in CNPG 1.31, so it is not used.
- Database volumes are local-path volumes, see [ADR 0005](0005-local-path-on-zfs-instead-of-longhorn.md). The R2
  backups, with WAL archiving, are the restore path when the node or its disk is lost.
- The Postgres tasks in the Ansible playbook, the Pulumi role code and the `applications/bootstrap/postgres/`
  EndpointSlice go away. Existing data, such as cost-tracker's, has to be dumped from the Pi and restored into CNPG,
  or the app starts fresh.
- Moving off CNPG later means migrating live data, which is why this is recorded.
