# Traefik

*Primary audience: Persona 2*

## What is it?

Traefik is the front door of the home lab. Every request from a browser — whether to ArgoCD or any other service — arrives at Traefik first. Traefik looks at the hostname (e.g. `argocd.neustrom.net`) and forwards the request to the right service running in the cluster.

This role is called a **reverse proxy** or **ingress controller**.

Think of it like a hotel reception desk. Guests arrive and say where they're going; the receptionist directs them to the right room. Traefik receives web requests and routes them to the right application.

## Why is it here?

Multiple services need to be accessible over HTTPS on the same server. Without a reverse proxy, each service would need its own port (`:8080`, `:8443`, etc.), which is awkward and hard to remember. Traefik lets everything use the standard HTTPS port (443) and routes based on the domain name instead.

Traefik also handles **TLS termination** — it decrypts incoming HTTPS traffic using the wildcard certificate provided by cert-manager, then forwards plain HTTP to the services internally. Services don't need to know anything about certificates.

## How is it deployed?

Traefik comes **pre-installed with k3s** and is not managed by ArgoCD. It cannot be removed without disabling it in the k3s configuration and redeploying it manually.

What *is* managed in this repo is the configuration layered on top:

- **`applications/bootstrap/argocd/middleware.yaml`** — a Traefik middleware that redirects HTTP traffic to HTTPS
- **`applications/vendor/traefik-certs/`** — the `Certificate` resource (requesting the wildcard cert from cert-manager) and the `TLSStore` (telling Traefik to use that cert as its default for all services)

## TLS termination

Because Traefik handles TLS centrally, new services added to the cluster get HTTPS automatically. No certificate configuration is needed on individual ingress resources — just a hostname and Traefik handles the rest.

See [Certificates Deep-Dive](../reference/certificates.md) for the full technical details.
