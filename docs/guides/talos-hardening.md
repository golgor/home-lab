# Talos Cluster Hardening

Hardening baseline for the Talos cluster on the Proxmox host. It carries over the parts of the earlier
security-hardening draft (#13) that still apply to the target architecture. Read it alongside
[ADR 0001](../adr/0001-tunnel-and-authentik-for-household-admin-lan-only.md) (exposure) and
[ADR 0002](../adr/0002-external-secrets-with-bitwarden-instead-of-sealed-secrets.md) (secrets).

## Scope

- **In scope:** household apps published through the Cloudflare Tunnel, Traefik, workloads in the cluster.
- **Out of scope:** admin surfaces (ArgoCD, Traefik dashboard, Proxmox, Talos and Kubernetes APIs, Pi-hole). They
  stay LAN-only and never get a tunnel route, so nothing below exposes them.
- **Handled by Talos by design:** the k3s-era items (kubeconfig file permissions, kubelet bind address, host SSH
  hardening, CrowdSec/fail2ban on the host). Talos has no shell or SSH, an immutable OS, and API access through
  mTLS `talosconfig`. Keep `talosconfig` and kubeconfig out of the repo.

## Why a tunnel, not a DNS proxy

Proxied DNS records (orange cloud) still need an inbound port on the router, and the origin IP can leak. The
Cloudflare Tunnel (`cloudflared`) dials out, so:

- no inbound ports or port forwards, which also works behind CGNAT;
- the origin IP is never published;
- only hostnames listed in the tunnel config are reachable; everything else gets a 404 from Cloudflare.

The tunnel token comes from Bitwarden Secrets Manager through an `ExternalSecret` (never a SealedSecret, never
committed):

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: cloudflared-token
  namespace: cloudflared
spec:
  secretStoreRef:
    kind: ClusterSecretStore
    name: bitwarden
  target:
    name: cloudflared-token
  data:
    - secretKey: token
      remoteRef:
        key: cloudflared-tunnel-token # Bitwarden secret name, not the value
```

Point every tunnel hostname at Traefik, not at a Service directly, so the middlewares below always apply.

## One auth method per public app

Each household app behind the tunnel uses exactly one gate:

| Gate | When | How |
| --- | --- | --- |
| Authentik forward-auth | App has no usable SSO | Traefik `forwardAuth` middleware on the IngressRoute |
| App-native OIDC | App logs in against Authentik itself (e.g. Home Assistant) | Explicit annotation on the route |

Never stack both on one app; double logins break mobile clients and API tokens. CI fails a public route that has
neither forward-auth nor the annotation. Example annotation (exact key is set by the CI check):

```yaml
metadata:
  annotations:
    neustrom.net/auth: app-oidc
```

Machine-to-machine access keeps working: cost-tracker's API must still accept Glance's bearer token
(`GLANCE_API_KEY`). If cost-tracker gets forward-auth, exclude the API path or keep it LAN-only.

## Traefik

### Insecure API off

```yaml
# Traefik Helm values
api:
  dashboard: true
  insecure: false
ports:
  traefik:
    expose:
      default: false
```

Nothing listens publicly on 9000. If the dashboard is needed, serve it via an IngressRoute to `api@internal`
on a LAN-only entrypoint.

### Security headers

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: security-headers
  namespace: traefik
spec:
  headers:
    stsSeconds: 31536000
    stsIncludeSubdomains: true
    frameDeny: true
    contentTypeNosniff: true
    referrerPolicy: strict-origin-when-cross-origin
    permissionsPolicy: "camera=(), microphone=(), geolocation=()"
```

### Rate limiting

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
  namespace: traefik
spec:
  rateLimit:
    average: 50
    burst: 100
```

Attach both to every public IngressRoute (or as defaults on the `websecure` entrypoint). Tune per app if needed.

### Access logging

```yaml
logs:
  access:
    enabled: true
    format: json
    fields:
      headers:
        defaultMode: drop
        names:
          User-Agent: keep
          Cf-Connecting-Ip: keep
```

Drop headers by default so cookies and `Authorization` never reach the logs.

## Workloads

### NetworkPolicies

Default deny per app namespace, then allow only what the app needs (ingress from Traefik, egress to DNS,
its CloudNativePG cluster, named external APIs).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

Requires a CNI that enforces policies; check the Talos CNI choice before relying on this.

### Pod securityContext

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
```

Add an `emptyDir` for paths the app must write to when using a read-only root filesystem.

### Pod Security Admission

Talos enables PSA with `baseline` enforced cluster-wide. Label app namespaces stricter:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

Keep `baseline` or `privileged` only for namespaces that need it (CNI, storage provisioner) and note why in the
manifest.

### Pin images

No `latest` or floating tags. Pin a version tag, ideally with digest (`image: app:1.2.3@sha256:...`), and let
Renovate propose bumps as PRs.

## Optional: Cloudflare Access

Cloudflare Access in front of a tunnel hostname adds an edge check before traffic reaches the cluster. It is an
extra layer, not a replacement for Authentik (ADR 0001). Consider it for apps with weak native auth.

## Verification checklist

- [ ] No router port forwards; tunnel shows healthy in Cloudflare.
- [ ] Tunnel config lists only household hostnames; no admin surface resolves publicly.
- [ ] `cloudflared` token is an `ExternalSecret`; no tunnel credential in git.
- [ ] Every public route has forward-auth or the app-native OIDC annotation; CI check passes.
- [ ] Traefik `api.insecure` is false; port 9000 not reachable from outside the cluster.
- [ ] Response headers include HSTS, `X-Frame-Options`, `X-Content-Type-Options`.
- [ ] Bursting requests at a public host returns 429.
- [ ] Each app namespace has a default-deny NetworkPolicy and the app still works.
- [ ] App namespaces enforce PSA `restricted`, or exceptions are documented.
- [ ] No floating image tags in `applications/`.
- [ ] Traefik access logs are JSON and contain no auth headers.
- [ ] Glance still loads cost-tracker data with `GLANCE_API_KEY`.

## Dropped from #13

Pi/DietPi and k3s config, Pulumi state backup, host Postgres SSL (replaced by CloudNativePG, ADR 0007),
SealedSecret tunnel token (ADR 0002), and forward-auth over the tunnel for ArgoCD, Traefik and Pi-hole (LAN-only
per ADR 0001).
