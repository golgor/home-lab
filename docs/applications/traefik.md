# Traefik

## What is it?

Traefik is the front door of the home lab. Every request from a browser — whether to ArgoCD or any other service — arrives at Traefik first. Traefik looks at the hostname (e.g. `argocd.neustrom.net`) and forwards the request to the right service running in the cluster.

This role is called a **reverse proxy** or **ingress controller**.

Think of it like a hotel reception desk. Guests arrive and say where they're going; the receptionist directs them to the right room. Traefik receives web requests and routes them to the right application.

## Why is it here?

Multiple services need to be accessible over HTTPS on the same server. Without a reverse proxy, each service would need its own port (`:8080`, `:8443`, etc.), which is awkward and hard to remember. Traefik lets everything use the standard HTTPS port (443) and routes based on the domain name instead.

Traefik also handles **TLS termination** — it decrypts incoming HTTPS traffic using the wildcard certificate provided by cert-manager, then forwards plain HTTP to the services internally. Services don't need to know anything about certificates.

## How is it deployed?

Traefik is deployed as an **ArgoCD-managed Helm chart** in the `traefik` namespace — it is not the k3s default Traefik. k3s is started with `--disable=traefik` to prevent conflicts.

Everything lives in `applications/vendor/traefik/`:

- **`values.yaml`** — Helm chart configuration
- **`certificate.yaml`** — requests the `*.neustrom.net` wildcard cert from cert-manager
- **`tlsstore.yaml`** — tells Traefik to use that cert as the default for all services
- **`dashboard-ingressroute.yaml`** — exposes the Traefik dashboard at `traefik.neustrom.net/dashboard/`
- **`middleware-errors.yaml`** — global error page middleware applied to all traffic

## Routing

Traefik supports three routing mechanisms, all enabled simultaneously:

| Provider | Resource kind | Used for |
|---|---|---|
| `kubernetesGateway` | `HTTPRoute` | Primary — new services should use this |
| `kubernetesCRD` | `IngressRoute`, `Middleware` | Traefik-specific features (e.g. error pages, dashboard) |
| `kubernetesIngress` | `Ingress` | Legacy — ArgoCD still uses this |

HTTP traffic on port 80 is redirected to HTTPS globally at the entrypoint level — no per-route middleware needed.

## TLS termination

Because Traefik handles TLS centrally, new services added to the cluster get HTTPS automatically. Route resources only need a hostname — no `tls:` block, no cert-manager annotations. Traefik picks up the default certificate from the `TLSStore` and does the rest.

See [Certificates Deep-Dive](../reference/certificates.md) for the full technical details.

## Error pages

Unrecognised hostnames and paths return a custom 404 page via a low-priority catch-all `HTTPRoute` in the `error-pages` namespace. All other HTTP errors (401, 403, 500–599) are intercepted globally by the `default-errors` Traefik middleware applied to the `websecure` entrypoint.
