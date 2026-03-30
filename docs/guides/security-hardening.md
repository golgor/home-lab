# Security Hardening for External Access

This guide documents the security review and hardening plan for exposing the home
lab to the internet via Cloudflare Tunnel. It covers every identified gap, the
rationale behind each fix, and the specific files to modify.

**Status:** Plan only -- not yet implemented.

---

## Why Cloudflare Tunnel (not DNS proxy)

There is no static IP from the ISP, which rules out traditional Cloudflare DNS
proxy (A record pointing to a public IP). Even if there were a static IP, Cloudflare
Tunnel is the better choice:

| | DNS Proxy (A record) | Cloudflare Tunnel |
| --- | --- | --- |
| Router ports | Must forward 80/443 | **None** -- outbound only |
| Home IP | Exposed in DNS records | **Hidden** -- CNAME to tunnel ID |
| Bypass risk | Attacker can hit IP directly, skip Cloudflare | **Cannot bypass** -- no open ports |
| Dynamic IP | Needs DDNS | **No problem** -- tunnel reconnects |
| Free tier | Yes | **Yes** |

`cloudflared` runs as a pod in the cluster and makes an **outbound-only**
connection to Cloudflare's edge network. Traffic can only reach internal services
through the tunnel. This eliminates an entire class of bypass attacks.

```mermaid
flowchart LR
    subgraph Internet
        Browser
        CF[Cloudflare Edge]
    end
    subgraph Home Network
        subgraph k3s Cluster
            CFD[cloudflared pod]
            T[Traefik]
            AUTH[Authentik]
            APPS[Applications]
        end
    end

    Browser -->|HTTPS| CF
    CF -->|Tunnel| CFD
    CFD -->|HTTP| T
    T -->|forward-auth check| AUTH
    T -->|route| APPS

    style CF fill:#f96,color:#000
    style CFD fill:#69f,color:#000
    style T fill:#6c6,color:#000
    style AUTH fill:#c6f,color:#000
```

**Routing strategy:** Tunnel -> Traefik (single catch-all rule). This preserves all
existing IngressRoute configs, middlewares, and TLS handling. Cloudflare SSL mode
set to "Full" (Traefik terminates TLS internally).

---

## Authentication Strategy

**Principle:** Every service must have at least one authentication layer. Use
exactly one method per user-facing app to avoid login friction. Add a second
layer only for critical admin tools (ArgoCD, Traefik dashboard) where a
compromise means full cluster control.

Two authentication methods are available:

| Method | How it works | Best for |
| --- | --- | --- |
| **Authentik forward-auth** | Traefik middleware checks SSO cookie before routing | Apps with no built-in auth (Glance, Pi-hole) |
| **App-native auth (OIDC)** | App handles its own login via Authentik as OIDC provider | Apps with built-in OIDC (cost-tracker) |

Both use Authentik as the identity provider -- the user logs in once and the
SSO cookie covers all `*.neustrom.net` apps (domain-level forward-auth).

```mermaid
sequenceDiagram
    participant User
    participant Traefik
    participant Authentik
    participant App as Application

    User->>Traefik: GET app.neustrom.net
    Traefik->>Authentik: Forward-auth check
    alt Not logged in
        Authentik->>User: 302 redirect to auth.neustrom.net
        User->>Authentik: SSO login
        Authentik->>User: Set cookie + redirect back
    end
    Authentik->>Traefik: 200 OK + user headers
    Traefik->>App: Forward request
    App->>User: Response
```

### Per-service auth plan

| Service | Host | Current auth | After hardening | Layers |
| --- | --- | --- | --- | --- |
| **Glance** | `neustrom.net` | **None** | Forward-auth | 1 |
| **Cost-tracker** | `costs.neustrom.net` | OIDC only | OIDC (already has it) | 1 |
| **Pi-hole** | `pihole.neustrom.net` | Forward-auth | Forward-auth (no change) | 1 |
| **Authentik** | `auth.neustrom.net` | Own login | Own login (no change) | 1 |
| **ArgoCD** | `argocd.neustrom.net` | Own login only | Forward-auth + built-in login | 2 |
| **Traefik** | `traefik.neustrom.net` | Forward-auth | Forward-auth (no change) | 1+ |

!!! info "Why two layers for ArgoCD?"
    ArgoCD has **cluster-admin privileges** -- it can deploy any manifest, read
    any secret, and modify any resource. It has had auth bypass CVEs in the past
    (e.g., CVE-2024-31990). A second layer (forward-auth) ensures an ArgoCD
    auth bug alone cannot grant cluster control. The Traefik dashboard already
    has forward-auth, so it keeps its existing protection.

!!! info "Why one layer is enough for user apps"
    Cost-tracker and Glance are user-facing apps with limited blast radius. A
    compromised cost-tracker exposes financial data but not cluster control.
    Adding forward-auth on top of OIDC would mean two login prompts, which
    adds friction for mobile use (the primary use case). One solid auth
    layer is sufficient -- the real defense against lateral movement comes
    from NetworkPolicies and pod security (see below).

---

## Critical Fixes

These must be done before exposing the cluster externally. Each represents a
direct path to compromise if left unaddressed.

### 1. Deploy Cloudflare Tunnel

**Gap:** No mechanism to route external traffic to the cluster without opening
router ports.

**Fix:** Deploy `cloudflared` as a Kubernetes Deployment.

New files to create:

```text
applications/vendor/cloudflared/
├── application.yaml                          # ArgoCD Application
├── kustomization.yaml                        # Kustomize manifest
├── deployment.yaml                           # cloudflared pod
└── tunnel-credentials-sealedsecret.yaml      # Tunnel token (sealed)
```

The tunnel config maps all traffic to Traefik's internal service:

```yaml
# Tunnel ingress config (in ConfigMap or as args)
ingress:
  - service: http://traefik.traefik.svc.cluster.local
```

On the Cloudflare dashboard:

1. Create a tunnel in Zero Trust > Networks > Tunnels
2. Copy the tunnel token
3. Seal the token and commit as a SealedSecret
4. Change all `*.neustrom.net` DNS records from A records to CNAMEs
   pointing to `<tunnel-id>.cfargotunnel.com`

### 2. Fix kubeconfig permissions

**Gap:** `write-kubeconfig-mode: "644"` in `diet-pi/k3s-config.yaml` makes the
kubeconfig world-readable on the host.

**Why this matters:** Any process on the DietPi host -- even a low-privilege one
-- can read `/etc/rancher/k3s/k3s.yaml` and get full **cluster-admin** access.
This is the difference between a container escape giving "host-level access" vs
"host-level access + full cluster control over every pod, secret, and namespace."

**Fix:**

```yaml
# diet-pi/k3s-config.yaml
write-kubeconfig-mode: "600"  # was "644"
```

Then re-apply via Ansible and restart k3s.

### 3. Disable Traefik insecure API and close port 9000

**Gap:** Two settings in `applications/vendor/traefik/values.yaml`:

- `api.insecure: true` (line 50) -- exposes the Traefik dashboard/API without TLS
  or authentication on port 9000
- `ports.traefik.expose.default: true` (line 61) -- makes port 9000 accessible on
  the LoadBalancer service, not just cluster-internal

Together, these expose the **full Traefik API** to anyone on the network. The API
reveals:

- Complete routing table (every hostname -> service mapping)
- All middleware configurations (including auth endpoints)
- Internal service addresses and namespaces
- Certificate details

This is a reconnaissance goldmine for an attacker.

**Fix:**

```yaml
# applications/vendor/traefik/values.yaml
api:
  dashboard: true
  insecure: false  # was true

ports:
  traefik:
    port: 9000
    expose:
      default: false  # was true
```

The dashboard remains accessible through the authenticated IngressRoute at
`traefik.neustrom.net` (defined in `dashboard-ingressroute.yaml`, which already
has `authentik-forwardauth` middleware).

### 4. Add forward-auth to ArgoCD

**Gap:** `applications/bootstrap/argocd/ingress.yaml` uses a standard
`networking.k8s.io/v1` Ingress with no authentication middleware. ArgoCD relies
solely on its built-in login.

**Why this matters:** ArgoCD has **cluster-admin privileges**. It can deploy any
manifest to any namespace, read all secrets, and modify any resource. It is the
single most powerful tool in the cluster. Relying on one auth layer for the most
critical service is insufficient when internet-facing.

ArgoCD has had auth bypass CVEs in the past (e.g., CVE-2024-31990, CVE-2023-22482).
A single such vulnerability would give an attacker full cluster control.

**The recommendation is NOT to replace ArgoCD's login.** It is to add forward-auth
as a second layer in front:

```mermaid
sequenceDiagram
    participant User
    participant Traefik
    participant Authentik
    participant ArgoCD

    User->>Traefik: GET argocd.neustrom.net
    Traefik->>Authentik: Forward-auth check
    alt Not SSO-authenticated
        Authentik->>User: Redirect to login
    end
    Authentik->>Traefik: 200 OK
    Traefik->>ArgoCD: Forward request
    Note over ArgoCD: ArgoCD's own login page appears
    User->>ArgoCD: Log in with ArgoCD credentials
```

An attacker must now bypass both Authentik SSO **and** ArgoCD's own auth.

**Fix:** Convert the Ingress to a Traefik IngressRoute with forward-auth. The
current Ingress:

```yaml
# applications/bootstrap/argocd/ingress.yaml (CURRENT)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik
  rules:
    - host: argocd.neustrom.net
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 80
```

Replace with:

```yaml
# applications/bootstrap/argocd/ingress.yaml (PROPOSED)
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: argocd-server
  namespace: argocd
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`argocd.neustrom.net`)
      kind: Rule
      middlewares:
        - name: authentik-forwardauth
          namespace: authentik
      services:
        - name: argocd-server
          port: 80
```

!!! warning "Bootstrap resource"
    ArgoCD is a bootstrap resource -- it is not managed by ArgoCD itself. After
    changing this file, you must re-apply manually:
    ```bash
    kustomize build --enable-helm applications/bootstrap/argocd \
      | kubectl apply --server-side --force-conflicts -f -
    ```

### 5. Add forward-auth to Glance

**Gap:** `applications/vendor/glance/ingressroute.yaml` has **zero authentication**.
Glance has no built-in auth at all.

**What Glance exposes to anyone who visits `neustrom.net`:**

- Personal financial data from cost-tracker API (monthly expenses, balances)
- Calendar events (personal ICS URL)
- Internal cluster service names and health status
- Pi-hole DNS statistics
- Kubernetes deployment/node information

**Fix:** Add the same middleware used by Pi-hole and the Traefik dashboard:

```yaml
# applications/vendor/glance/ingressroute.yaml (PROPOSED)
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: glance
  namespace: glance
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`neustrom.net`)
      kind: Rule
      middlewares:
        - name: authentik-forwardauth
          namespace: authentik
      services:
        - name: glance
          port: 8080
```

### 6. Verify cost-tracker has auth

**Status:** Cost-tracker on branch `claude/deploy-cost-tracker-app-2qfJs` already
has built-in OIDC (`OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` env
vars in the deployment). This is sufficient as a single auth layer.

**No forward-auth needed** -- cost-tracker is a user-facing app, not an admin
tool. Adding forward-auth on top of OIDC would mean two login prompts, hurting
the mobile use case. The OIDC integration uses Authentik as the identity
provider, so it benefits from the same SSO session.

**Verify when merging:** Confirm that the OIDC configuration is correct and
that unauthenticated API requests (e.g., `/api/v1/summary`) return 401.
The Glance dashboard calls cost-tracker's API with a bearer token
(`GLANCE_API_KEY`), so API-key-based access must remain functional for
internal cluster traffic.

---

## High-Priority Fixes

Should be done before or immediately after exposing. These significantly reduce
risk but the cluster can survive briefly without them.

### 7. Security headers middleware

**Gap:** No security headers are applied to any response. This enables several
browser-based attacks:

| Missing header | Attack enabled |
| --- | --- |
| `Strict-Transport-Security` (HSTS) | SSL stripping on same WiFi |
| `X-Frame-Options` | Clickjacking (embedding admin UIs in iframes) |
| `X-Content-Type-Options` | MIME type confusion attacks |
| `Content-Security-Policy` | XSS execution |
| `Referrer-Policy` | Leaking internal URLs in referrer headers |
| `X-Robots-Tag` | Search engines indexing private services |

**Fix:** Create `applications/vendor/traefik/middleware-security-headers.yaml`:

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
    stsPreload: true
    forceSTSHeader: true
    contentTypeNosniff: true
    frameDeny: true
    browserXssFilter: true
    referrerPolicy: "strict-origin-when-cross-origin"
    permissionsPolicy: "camera=(), microphone=(), geolocation=()"
    customResponseHeaders:
      X-Robots-Tag: "noindex, nofollow"
```

Add to `applications/vendor/traefik/kustomization.yaml` resources and as a
default middleware on the websecure entrypoint in `values.yaml`:

```yaml
# applications/vendor/traefik/values.yaml (add to websecure middlewares)
ports:
  websecure:
    http:
      middlewares:
        - "traefik-default-errors@kubernetescrd"
        - "traefik-security-headers@kubernetescrd"
```

!!! note "CSP tuning"
    The Content-Security-Policy may need per-app tuning. Start without CSP in
    the global middleware, add it per-app as needed via additional middlewares
    chained on specific IngressRoutes.

### 8. Rate limiting middleware

**Gap:** No rate limiting anywhere. Brute-force attacks against Authentik login
or any API endpoint are unconstrained. Cloudflare free tier has only 1 rate-
limiting rule, insufficient for per-endpoint protection.

**Fix:** Create `applications/vendor/traefik/middleware-ratelimit.yaml`:

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: default-ratelimit
  namespace: traefik
spec:
  rateLimit:
    average: 50
    burst: 100
    period: 1m
```

Add as a default middleware on the websecure entrypoint (same as security
headers above).

### 9. NetworkPolicies

**Gap:** Zero NetworkPolicies in the cluster. Every pod can communicate with
every other pod across all namespaces. If any container is compromised, the
attacker can directly reach Authentik, ArgoCD, PostgreSQL, and every other
service.

**Design:** Default-deny ingress in every namespace, then explicit allow rules:

| Namespace | Allowed ingress from | Port |
| --- | --- | --- |
| `traefik` | cloudflared pod | 443 |
| `authentik` | Traefik | 80 |
| `argocd` | Traefik | 80 |
| `glance` | Traefik | 8080 |
| `pihole` | Traefik (web), local network (DNS) | 80, 53 |
| `databases` | Authentik, cost-tracker pods | 5432 |
| `cost-tracker` | Traefik | 8000 |

!!! danger "Flannel does not support NetworkPolicies"
    k3s uses Flannel by default. Flannel accepts NetworkPolicy resources but
    **silently ignores them**. To enforce NetworkPolicies, you must install a
    CNI that supports them:

    - **Option A:** Install Calico alongside Flannel (overlay mode)
    - **Option B:** Restart k3s with `--flannel-backend=none` and install
      Calico or Cilium from scratch

    This is the most disruptive change in the plan but also one of the most
    important. Without NetworkPolicies, a compromised pod can directly
    attack every other service in the cluster. This is the primary defense
    against lateral movement.

### 10. Bind kubelet to node IP

**Gap:** `node-ip=0.0.0.0` in `diet-pi/k3s-config.yaml` binds the kubelet
API to all network interfaces.

**Fix:**

```yaml
# diet-pi/k3s-config.yaml
kubelet-arg:
  - "node-ip=10.0.0.110"  # was 0.0.0.0
```

---

## Medium-Priority Fixes

Address these soon after initial exposure. They add defense-in-depth layers
that limit blast radius if an attacker gains a foothold.

### 11. Pod security contexts

**Gap:** No deployment specifies security contexts. Containers run as root
with full Linux capabilities and writable root filesystems.

**Fix:** Add to all deployments:

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
```

**Affected files:**

- `applications/vendor/glance/deployment.yaml`
- `applications/vendor/error-pages/deployment.yaml`
- `applications/custom/cost-tracker/deployment.yaml` (on branch)
- Helm apps: set via `values.yaml` securityContext options

!!! note "readOnlyRootFilesystem"
    Some apps need writable temp directories. Add an `emptyDir` volume
    mounted at `/tmp` for those cases. Test each app individually.

### 12. Pod Security Admission (PSA)

**Gap:** No cluster-level enforcement prevents over-privileged pods.

**Fix:** Add namespace labels:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

Start with `warn` on all namespaces, fix violations, then switch to `enforce`.
Use `baseline` instead of `restricted` for namespaces that need elevated
privileges (e.g., Traefik needs `NET_BIND_SERVICE`).

### 13. PostgreSQL SSL

**Gap:** `sslmode="disable"` in `infrastructure/__main__.py` line 14. All
database traffic is unencrypted.

Currently acceptable because PostgreSQL runs as a Docker container on the same
host (10.0.0.110). However, the database listens on all interfaces and accepts
connections from the entire `10.0.0.0/24` subnet. If an attacker gains access
to any device on the local network, they can sniff database credentials.

**Fix:**

1. Enable SSL in PostgreSQL via the Ansible playbook
2. Remove `sslmode="disable"` in `infrastructure/__main__.py` (the default
   `sslmode="require"` in `infrastructure/postgresql_config/__init__.py`
   will then apply)
3. Update Authentik's database connection to use SSL

### 14. Full access logging

**Gap:** Traefik access logs only capture status codes 400-599
(`applications/vendor/traefik/values.yaml` lines 86-89). Successful requests
are not logged, making incident investigation nearly impossible.

**Fix:**

```yaml
# applications/vendor/traefik/values.yaml
logs:
  access:
    enabled: true
    # Remove statuscodes filter to log ALL requests
```

### 15. Pin floating image tags

**Gap:** `applications/vendor/glance/deployment.yaml` line 48 uses
`ghcr.io/awildleon/glance-ical-events:latest`. The `:latest` tag can change
at any time -- a supply chain attack could replace it with a malicious image.

**Fix:** Pin to a specific version tag or image digest.

---

## Nice-to-Have (Optional Further Hardening)

### 16. Cloudflare Access (Zero Trust)

Adds an additional auth gate at Cloudflare's edge -- before traffic reaches the
tunnel. Free for up to 50 users. Useful if you want an extra layer on top of
Authentik, but adds another login step.

Setup: Zero Trust dashboard > Access > Applications > `*.neustrom.net`. Exempt
`auth.neustrom.net` (otherwise OIDC redirects break in a loop).

### 17. CrowdSec or fail2ban on the host

Even behind Cloudflare Tunnel, the DietPi host has SSH exposed on the local
network. CrowdSec or fail2ban can detect and block brute-force attempts.

### 18. Backup Pulumi local state

Pulumi state in `~/.pulumi/` has no automatic backup. Losing it means manual
`pulumi import` for every resource. Set up a cron job to an encrypted offsite
backup.

---

## Verification Checklist

After implementing the plan, verify with:

- [ ] **Port scan home IP** -- confirm no open ports (no port forwarding on router)
- [ ] **Test unauthenticated access** -- hit each URL without cookies, confirm
      redirect to Authentik or OIDC login
- [ ] **Check security headers** -- `curl -I https://neustrom.net` should show
      HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- [ ] **Test rate limiting** -- rapid requests should eventually get 429 responses
- [ ] **Verify port 9000 closed** -- `curl http://10.0.0.110:9000` should fail
- [ ] **Confirm full access logs** -- check Traefik logs show 200 responses too
- [ ] **ArgoCD double auth** -- forward-auth redirects to Authentik, then ArgoCD's own login page
- [ ] **Cost-tracker OIDC** -- unauthenticated request returns 401, OIDC login works from mobile
- [ ] **Mobile test** -- access cost-tracker on cellular, confirm full auth flow
- [ ] **DNS records** -- all `*.neustrom.net` should be CNAMEs, no A records
      exposing the home IP

---

## Files to Modify (Summary)

| Priority | File | Change |
| --- | --- | --- |
| Critical | `diet-pi/k3s-config.yaml` | kubeconfig mode `600`, node-ip `10.0.0.110` |
| Critical | `applications/vendor/traefik/values.yaml` | `api.insecure: false`, close port 9000, add default middlewares, full logging |
| Critical | `applications/bootstrap/argocd/ingress.yaml` | Convert to IngressRoute + forward-auth |
| Critical | `applications/vendor/glance/ingressroute.yaml` | Add forward-auth middleware |
| Critical | `applications/vendor/cloudflared/` | **New** -- entire directory for tunnel |
| High | `applications/vendor/traefik/middleware-security-headers.yaml` | **New** -- security headers |
| High | `applications/vendor/traefik/middleware-ratelimit.yaml` | **New** -- rate limiting |
| High | `applications/vendor/traefik/kustomization.yaml` | Add new middleware resources |
| High | CNI installation (Calico/Cilium) | Required for NetworkPolicy enforcement |
| High | `networkpolicy.yaml` per namespace | **New** -- default-deny + allow rules |
| Medium | `applications/vendor/glance/deployment.yaml` | Pin `:latest` tag, add security context |
| Medium | `applications/vendor/error-pages/deployment.yaml` | Add security context |
| Medium | `infrastructure/__main__.py` | Remove `sslmode="disable"` |
| Medium | `ansible/playbook.yaml` | Enable PostgreSQL SSL |
