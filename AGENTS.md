# Home Lab

Mono-repo for home lab infrastructure based on k3s.

## Structure

- `ansible/` - Ansible playbooks for server provisioning
- `applications/` - Application/service configurations
  - `bootstrap/` - What you apply by hand to start a cluster
    - `argocd/` - ArgoCD (manually applied, not managed by ArgoCD)
    - `root.yaml` - Root app-of-apps: syncs itself, `vendor-apps.yaml` and `custom-apps.yaml`.
      Applied by hand once, then ArgoCD manages it
  - `bootstrap/postgres/` - Database Service + EndpointSlice (manually applied)
  - `vendor/` - Third-party apps managed by ArgoCD (App of Apps pattern)
    - `vendor-apps.yaml` - App of Apps, scans for `**/application.yaml`
    - `sealed-secrets/` - Bitnami Sealed Secrets
    - `cert-manager/` - cert-manager + Let's Encrypt ClusterIssuer (Cloudflare DNS challenge)
    - `traefik-certs/` - Wildcard Certificate + TLSStore for Traefik default TLS
    - `authentik/` - Authentik identity provider (SSO, forward-auth) — **currently disabled** (excluded in `vendor-apps.yaml`); access is gated by Tailscale instead. Files kept for easy re-enable.
  - `custom/` - Self-developed apps managed by ArgoCD (ApplicationSet pattern)
    - `custom-apps.yaml` - ApplicationSet, scans for directories under `applications/custom/*`
    - `cost-tracker/` - Household expense-sharing app
- `infrastructure/` - Single Pulumi project (Python/uv), one ComponentResource package per component
  - `postgres/` - PostgreSQL Docker container
  - `postgresql_config/` - Database management (roles, users, service accounts, grants)
- `docs/` - MkDocs Material documentation site

## Commands

```bash
mise run docs          # Serve docs with live reload
mise run fetch-cert    # Fetch kubeseal public cert from cluster (run after cluster re-install)
mise run seal-secret   # Interactively seal a secret from a .env file
```

## Bootstrap (manual, not managed by ArgoCD)

ArgoCD and the root app-of-apps must be applied manually once:

```bash
# Apply ArgoCD
kustomize build --enable-helm applications/bootstrap/argocd | kubectl apply --server-side --force-conflicts -f -

# Apply the root app-of-apps (ArgoCD then manages everything else, the root included)
kubectl apply -f applications/bootstrap/root.yaml

# Apply database endpoint (update IP in endpointslice.yaml first)
kubectl apply -k applications/bootstrap/postgres/
```

## Remote access (Tailscale)

No static IP at home. Remote access to `*.neustrom.net` is via **Tailscale** (personal tailnet), not port
forwarding or a Cloudflare Tunnel. **No cluster changes are needed to enable it** — it's node-level + DNS.

- The k3s node (`10.0.0.110`) is joined to the personal tailnet (`tailscale up`). Its tailnet IP is
  `tailscale ip -4` (currently `100.89.48.68`).
- Public Cloudflare wildcard `*.neustrom.net` A-record points at the node's **tailnet** IP, set **DNS-only
  (grey cloud, not proxied)**. At home, PiHole overrides `*.neustrom.net` → LAN IP `10.0.0.110`, so home
  traffic stays LAN-direct.
- Traefik serves tailnet traffic unchanged: klipper binds node ports 80/443 on all IPs, routing is by
  `Host`, and the wildcard cert is valid over any path (DNS-01 challenge).
- On clients (laptop/phone), keep Tailscale's DNS-override/MagicDNS **off** — public DNS already returns
  the tailnet IP, and leaving it off keeps the PiHole home-LAN path intact.

Full walkthrough: `docs/guides/remote-access-tailscale.md`.

## Infrastructure (Pulumi)

State is stored locally (`pulumi login --local`, stored in `~/.pulumi/`).

```bash
cd infrastructure
pulumi login --local               # one-time: use local state backend
pulumi stack init dev              # one-time: create a stack
pulumi config set --secret postgres:password <pw>  # one-time: set secrets
pulumi up                          # deploy
pulumi destroy                     # tear down
```

## Secrets workflow

Secrets are managed with Sealed Secrets. The `certs/cert.pem` is the cluster's public key (safe to commit).

1. Create a `.env` file with `KEY=value` pairs (never commit)
2. `mise run seal-secret` — generates `<name>-sealedsecret.yaml`
3. Move to the app directory, add to `kustomization.yaml`, push

On cluster re-install: run `mise run fetch-cert` first, then re-seal all secrets.

## Docs

- Config: `mkdocs.yml` (Material theme, mermaid diagrams supported)
- Pages defined in `nav:` section of `mkdocs.yml`
- Add new pages to `docs/` and register in `mkdocs.yml` nav tree
- See `docs/CLAUDE.md` for persona definitions and section→persona mapping

**After completing any meaningful work, update the docs:**

- `docs/applications/` — if a new app was added (add a page) or an existing app changed
- `docs/concepts/` — if a new concept was introduced that Persona 2 should understand
- `docs/reference/` — if operational details changed (commands, component locations, gotchas)
- `docs/get-started/` — if the bootstrap or setup process changed
- `README.md` — if the current state or next steps changed

## Gotchas

- **ArgoCD bootstrap is manual** — changes to `applications/bootstrap/argocd/` must be re-applied with kubectl, not pushed and waited on
- **The root app-of-apps syncs itself** — `applications/bootstrap/root.yaml` syncs itself plus `vendor/vendor-apps.yaml` and `custom/custom-apps.yaml`, so changes to any of them apply on push. Only re-apply it by hand to bootstrap or if the root can no longer find itself in git (e.g. after moving/renaming `bootstrap/root.yaml`). A new top-level Argo CD file must be added to the root's `include` list, or it will not sync.
- **`Prune=false,Delete=false` on root-synced files** — every file the root syncs carries this annotation, so an `include` typo, renamed file or deleted root cannot cascade through every Application. `Delete=false` alone does not stop a sync-time prune; keep both. Delete or rename these by hand.
- **Authentik is disabled, not deleted** — excluded via `exclude: "authentik/**"` in `vendor-apps.yaml`; access is gated by Tailscale instead. Deleting the ArgoCD Application did *not* cascade (no resources-finalizer), so its workloads were removed manually with `kubectl delete namespace authentik`. Its Postgres DB/role are **retained** in Pulumi. Re-enable: remove the exclude, re-apply `vendor-apps.yaml`, and re-add the `authentik-forwardauth` middleware refs (pihole + traefik dashboard IngressRoutes)
- **Cloudflare record for tailnet must be DNS-only** — the `*.neustrom.net` A-record pointing at the `100.x` tailnet IP must stay grey-cloud. Proxying (orange cloud) breaks it: Cloudflare's edge has no tailnet membership and cannot reach a private `100.x` address
- **Apex needs its own record** — a `*.neustrom.net` wildcard does **not** match the bare apex `neustrom.net` (wildcards cover one label to the left, not the apex). The root service (`/`) needs an explicit `neustrom.net` A-record (same DNS-only rule) and a Traefik route matching `Host(\`neustrom.net\`)`. PiHole's local wildcard (`address=/neustrom.net/10.0.0.110`) already covers the apex, so this gap is Cloudflare-only
- **Sealed Secrets CRD**: kustomize's `helm template` skips `crds/` — fixed with `includeCRDs: true` in the helmCharts entry
- **TLS is wildcard**: cert-manager issues `*.neustrom.net` stored in `kube-system`. Traefik's `TLSStore/default` serves it globally — no `tls:` block or cert-manager annotations needed on ingresses
- **kubeseal controller**: named `sealed-secrets` (not `sealed-secrets-controller`) in namespace `sealed-secrets`
- **Pulumi `depends_on`**: `PostgresqlConfig` must depend on the `Postgres` container to avoid connection failures during container replacements. Docker `wait=True` + `wait_timeout=30` ensures the container is healthy before downstream resources connect.
- **Pulumi grant concurrency**: PostgreSQL catalog errors (`tuple concurrently updated`) when grants run in parallel — all grants within a service account are chained sequentially via `depends_on`
- **Pulumi Docker log drift**: explicitly set `log_driver="json-file"` and `log_opts` to match Docker daemon defaults, otherwise Pulumi sees a diff and replaces the container on every `pulumi up`
- **Pulumi state is local**: stored in `~/.pulumi/`, not backed up automatically. Losing state means manual `pulumi import` or recreate from scratch.
- **Database SSL**: both Pulumi and workload connections currently use `sslmode=disable` (localhost Docker). `PostgresqlConfig` defaults to `require` — the call site overrides to `disable`. When PostgreSQL moves off-host, remove the override and update workload configs separately.
- **Pod DNS ≠ node DNS**: Pods use CoreDNS, not the node's `/etc/hosts`. If `*.neustrom.net` is only resolvable via PiHole and the RPi doesn't use PiHole as its DNS server, pods can't resolve those domains (e.g. OIDC issuer at `auth.neustrom.net`). Workaround: `hostAliases` in the pod spec. Proper fix: configure the RPi to use PiHole as its DNS server.
- **ghcr.io packages are private by default**: GitHub Container Registry packages default to private even when the source repo is public. Either make the package public in GitHub package settings, or create an `imagePullSecret` with a GitHub PAT.
