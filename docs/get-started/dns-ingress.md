# DNS & Ingress

## How It Works

Traefik is deployed as an ArgoCD-managed Helm application and acts as the cluster's ingress controller and
reverse proxy. When a request arrives, Traefik inspects the hostname and routes it to the correct service.

```text
Browser → argocd.neustrom.net → (DNS) → Node IP → Traefik → Service
```

## DNS Setup

All services are exposed under `*.neustrom.net`. DNS is managed in Cloudflare with an A record
pointing to the node's public IP.

For local access from machines on the same network, a wildcard DNS record on your local resolver
(Pi-hole, AdGuard Home, etc.) pointing `*.neustrom.net` to the node's LAN IP is sufficient.

!!! warning "The k3s node must also use the local resolver"
    Pods use CoreDNS, which inherits the node's DNS settings — not
    your laptop's. If the node (RPi) doesn't use PiHole as its DNS
    server, pods can't resolve `*.neustrom.net`. This breaks any
    server-side request to another cluster app (e.g. OIDC discovery
    against `auth.neustrom.net`).

    **Quick workaround:** add `hostAliases` in the pod spec to
    hard-code the mapping. **Proper fix:** configure the node's DNS to
    use PiHole.

## HTTP to HTTPS Redirect

HTTP→HTTPS redirection is handled globally at the Traefik entrypoint level — no per-route middleware
or annotation is needed. Any request on port 80 is automatically redirected to port 443.

## TLS

cert-manager issues a wildcard certificate (`*.neustrom.net`) via Let's Encrypt with a Cloudflare
DNS-01 challenge. The certificate is stored as a Secret in the `traefik` namespace.

Traefik's `TLSStore/default` references this secret, so all services get HTTPS automatically. Route resources
(HTTPRoute, Ingress, IngressRoute) do **not** need a `tls:` block or any cert-manager annotation.

## Routing

Three providers are active simultaneously:

| Provider | Resource kind | Used for |
| --- | --- | --- |
| `kubernetesGateway` | `HTTPRoute` | Primary — new services should use this |
| `kubernetesCRD` | `IngressRoute`, `Middleware` | Traefik-specific features (dashboard, error pages) |
| `kubernetesIngress` | `Ingress` | Legacy — ArgoCD still uses this |

### Adding a new service (HTTPRoute)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-app
  namespace: my-app
spec:
  parentRefs:
    - group: gateway.networking.k8s.io
      kind: Gateway
      name: traefik-gateway
      namespace: traefik
      sectionName: websecure
  hostnames:
    - my-app.neustrom.net
  rules:
    - backendRefs:
        - group: ""
          kind: Service
          name: my-app
          port: 8080
          weight: 1
```

!!! note
    Always include `group`/`kind` on both `parentRefs` and `backendRefs` and `weight` on `backendRefs`.
    Omitting them causes ArgoCD sync loops because Traefik fills in the defaults and ArgoCD detects drift.
