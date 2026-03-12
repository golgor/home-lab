# Home Lab

Mono-repo for home lab infrastructure based on k3s.

## Structure

- `ansible/` - Ansible playbooks for server provisioning
- `applications/` - Application/service configurations
  - `bootstrap/argocd/` - ArgoCD (manually applied, not managed by ArgoCD)
  - `vendor/` - Third-party apps managed by ArgoCD (App of Apps pattern)
    - `vendor-apps.yaml` - App of Apps, scans for `**/application.yaml`
    - `sealed-secrets/` - Bitnami Sealed Secrets
    - `cert-manager/` - cert-manager + Let's Encrypt ClusterIssuer (Cloudflare DNS challenge)
    - `traefik-certs/` - Wildcard Certificate + TLSStore for Traefik default TLS
  - `custom/` - Self-developed apps (separate repos, images on GitHub)
- `infrastructure/` - Infrastructure definitions
- `docs/` - MkDocs Material documentation site

## Commands

```bash
mise run docs          # Serve docs with live reload
mise run fetch-cert    # Fetch kubeseal public cert from cluster (run after cluster re-install)
mise run seal-secret   # Interactively seal a secret from a .env file
```

## Bootstrap (manual, not managed by ArgoCD)

ArgoCD and the vendor App of Apps must be applied manually once:

```bash
# Apply ArgoCD
kustomize build --enable-helm applications/bootstrap/argocd | kubectl apply --server-side --force-conflicts -f -

# Apply App of Apps (ArgoCD then manages everything else)
kubectl apply -f applications/vendor/vendor-apps.yaml
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
- **Sealed Secrets CRD**: kustomize's `helm template` skips `crds/` — fixed with `includeCRDs: true` in the helmCharts entry
- **TLS is wildcard**: cert-manager issues `*.neustrom.net` stored in `kube-system`. Traefik's `TLSStore/default` serves it globally — no per-ingress TLS config needed
- **kubeseal controller**: named `sealed-secrets` (not `sealed-secrets-controller`) in namespace `sealed-secrets`
