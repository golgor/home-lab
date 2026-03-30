# Cost Tracker

Cost Tracker is a household expense-sharing application. It helps two
partners track shared costs, see who owes whom, and settle up at the end
of each month.

## Why it exists

When two people share expenses, someone always ends up paying more than
their share. Cost Tracker keeps a running balance so both partners can
log purchases throughout the month and see a clear summary of what needs
to be settled.

## How it works

```mermaid
flowchart LR
    U[User] -->|costs.neustrom.net| CT[Cost Tracker]
    CT -->|stores expenses| DB[(PostgreSQL)]
    CT -->|login via| A[Authentik]
    G[Glance dashboard] -->|reads summary| CT
```

- **Cost Tracker** runs in the `cost-tracker` namespace and provides
  a web UI for logging expenses and viewing balances.
- **PostgreSQL** stores all expense data. The database runs outside the
  cluster (managed by Pulumi) and is reached via the
  `postgres.databases.svc.cluster.local` service.
- **Authentik** handles login via OpenID Connect (OIDC) — you sign in
  with the same account used for all other home lab apps.
- **Glance** can display a finance summary widget on the dashboard by
  calling the Cost Tracker API.

## Database migrations

The application uses Alembic to manage its database schema. Migrations
run automatically on every pod start via an **init container** — a small
setup step that runs before the main application launches. If the
database is already up to date, the migration is a no-op.

## DNS workaround

!!! warning "Temporary workaround"
    This should be removed once the RPi uses PiHole as its DNS server.

The cost-tracker pod needs to contact Authentik (`auth.neustrom.net`) for
OIDC login. However, pods inside the cluster use a different DNS system
(CoreDNS) than your computer. Your computer resolves `*.neustrom.net`
via PiHole, but the cluster node (RPi) doesn't use PiHole — so pods
can't find `auth.neustrom.net`.

As a workaround, the deployment includes a `hostAliases` entry that
hard-codes `auth.neustrom.net → 10.0.0.110` directly in the pod. This
is like adding a line to `/etc/hosts`, but for the pod only.

## Key details

| Key | Value |
| --- | --- |
| Namespace | `cost-tracker` |
| URL | [costs.neustrom.net](https://costs.neustrom.net) |
| Image | `ghcr.io/golgor/cost-tracker:1.0.0` |
| Port | 8000 |
| Database | `cost-tracker` (dedicated, managed by Pulumi) |
| Auth | OIDC via Authentik |
| Secrets | `cost-tracker-secrets` (SealedSecret with DB URL, OIDC credentials, API keys) |
| Config | ConfigMap `cost-tracker-config` (`LOG_LEVEL`, `ENV`) |
