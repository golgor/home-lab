# Upgrading

## Upgrading ArgoCD

1. Update the `version` field in `applications/bootstrap/argocd/kustomization.yaml`
2. Review the [ArgoCD changelog](https://github.com/argoproj/argo-cd/releases) for breaking changes
3. Re-apply the bootstrap:

```bash
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -
```

## Upgrading Vendor Apps

Update the chart version in the app's `kustomization.yaml` and commit.
ArgoCD will sync the change automatically.

!!! warning "Authentik: one release family per hop"
    Authentik refuses to migrate a database last seen more than one release
    family back (2026.2 → 2026.5 → 2026.8). The pod crash-loops with
    `Major version skips are not allowed`. Bump to the newest chart of each
    family in turn, one merge and sync per hop, and check the logs show the
    migrations finished before the next bump. Downgrades are unsupported, so
    back up the `authentik` database first.

### Traefik and the Gateway API CRDs

The Traefik chart no longer ships the Gateway API CRDs (since chart 40.2.0). They are vendored in
`applications/vendor/traefik/gateway-api-crds-v<version>.yaml` and must be bumped by hand to the version the
new Traefik release requires (see the [Traefik migration guide](https://doc.traefik.io/traefik/migrate/v3/)):

```bash
cd applications/vendor/traefik
curl -fsSL -o gateway-api-crds-v<new>.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v<new>/standard-install.yaml
git rm gateway-api-crds-v<old>.yaml
# update the resources: entry in kustomization.yaml, then check the render
kustomize build --enable-helm . | grep 'bundle-version'
```

The CRDs carry `Prune=false,Delete=false` (patched in `kustomization.yaml`), so a renamed or dropped file
leaves them in place. Deleting a CRD would delete every Gateway, GatewayClass and HTTPRoute.

!!! warning "No downgrades"
    The file also installs the `safe-upgrades.gateway.networking.k8s.io` ValidatingAdmissionPolicy. It rejects
    Gateway API CRDs older than its own bundle (v1.7.0 today) and experimental CRDs over standard ones, so
    rolling Traefik back to a chart that renders older CRDs fails to sync until that policy is removed.

## Upgrading k3s

TODO: Document k3s upgrade process.
