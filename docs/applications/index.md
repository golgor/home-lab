# Applications

Applications are divided into three categories:

- **Bootstrap** — manually applied before ArgoCD exists
- **Vendor** — third-party applications deployed from upstream Helm charts or manifests
- **Custom** — applications you develop and maintain yourself

Vendor and custom apps are managed by ArgoCD via the App of Apps pattern.

## App of Apps

The file `applications/vendor/vendor-apps.yaml` defines a root ArgoCD Application
that recursively scans `applications/vendor/` for `**/application.yaml` files.
Adding a new vendor app is as simple as creating a directory with an `application.yaml`
and pushing to Git.

## Current Applications

| Application | Type | Namespace | URL |
|------------|------|-----------|-----|
| ArgoCD | Bootstrap | `argocd` | [argocd.home-lab.local](https://argocd.home-lab.local) |
| Sealed Secrets | Vendor | `sealed-secrets` | — |
| cert-manager | Vendor | `cert-manager` | — |
