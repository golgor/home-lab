# Authentik

Authentik is an identity provider — it handles user accounts, logins, and
access control for all the other applications in the cluster. Think of it
as the "bouncer" that decides who is allowed to use what.

## Why it exists

Without Authentik, every application would need its own login system.
Authentik provides a single sign-on (SSO) experience: you log in once at
`auth.neustrom.net` and all connected applications recognise you.

It can also protect applications that have no built-in login at all, by
sitting in front of them and requiring authentication before traffic is
allowed through (this is called *forward authentication*).

## How it works

```mermaid
flowchart LR
    U[User] -->|auth.neustrom.net| A[Authentik]
    A -->|authenticated| App[Protected App]
    A -->|stores users/config| DB[(PostgreSQL)]
```

- **Authentik server** runs in the `authentik` namespace and handles the
  web UI, API, and authentication flows.
- **PostgreSQL** stores all user accounts, groups, and configuration. It
  runs outside the cluster (managed by Pulumi) and is reached via the
  `postgres.databases.svc.cluster.local` service.
- **Forward-auth middleware** is a Traefik middleware that intercepts
  requests to other apps, checks with Authentik whether the user is
  logged in, and either lets the request through or redirects to the
  login page. A single **domain-level** provider covers all
  `*.neustrom.net` apps — no per-app configuration needed in Authentik.

## Initial setup

On first deployment, navigate to
[auth.neustrom.net/if/flow/initial-setup/](https://auth.neustrom.net/if/flow/initial-setup/)
to create the `akadmin` admin account. This wizard is only available
before the initial admin user is configured.

After that, the admin interface is at
[auth.neustrom.net/if/admin/](https://auth.neustrom.net/if/admin/).

## Key details

| Key | Value |
| --- | --- |
| Namespace | `authentik` |
| URL | [auth.neustrom.net](https://auth.neustrom.net) |
| Helm chart | `authentik` from `charts.goauthentik.io` |
| Database | `authentik` (dedicated, managed by Pulumi) |
| Secrets | `authentik-application-secrets` (SealedSecret with DB password and secret key) |
| Forward-auth | Domain-level provider covering `*.neustrom.net` |
| Middleware | `authentik-forwardauth` in `authentik` namespace |

## Protecting apps

Any app can be protected by adding the forward-auth middleware to its
route — one annotation for HTTPRoute, or a `middlewares` block for
IngressRoute. See the
[Configuring Authentik Forward Auth](../guides/authentik.md) guide for
both syntaxes and full setup instructions.
