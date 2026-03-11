# Bootstrap

Bootstrapping is the process of getting the cluster from bare k3s to a
fully GitOps-managed state. Two components need manual bootstrapping:

1. **ArgoCD** — cannot deploy itself (chicken-and-egg problem)
2. **Vendor Apps (App of Apps)** — the root Application that tells ArgoCD to scan for vendor apps

After these two are applied, everything else is managed by ArgoCD via Git.

## Step 1: Deploy ArgoCD

```bash
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -
```

!!! note "Why `--server-side --force-conflicts`?"
    The ArgoCD CRDs exceed the 262KB annotation limit imposed by client-side
    `kubectl apply`. Server-side apply avoids this limitation by not storing
    the `last-applied-configuration` annotation.

Verify ArgoCD is running:

```bash
kubectl get pods -n argocd
```

### Getting the Admin Password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

The ArgoCD UI is available at [https://argocd.home-lab.local](https://argocd.home-lab.local)
(requires DNS — see [DNS & Ingress](dns-ingress.md)).

## Step 2: Apply the App of Apps

```bash
kubectl apply -f applications/vendor/vendor-apps.yaml
```

This creates a root ArgoCD Application that recursively scans
`applications/vendor/` for `**/application.yaml` files. Each vendor app
is automatically discovered and deployed.

## What Gets Deployed

### ArgoCD Bootstrap (`applications/bootstrap/argocd/`)

- ArgoCD Helm chart (version defined in `kustomization.yaml`)
- The `argocd` namespace
- A Traefik Ingress for `argocd.home-lab.local`
- A Traefik Middleware that redirects HTTP to HTTPS
- Kustomize build options (`--enable-helm`) for ArgoCD's repo server

### Vendor Apps (via App of Apps)

- **Sealed Secrets** — encrypts secrets so they can be stored in Git
- **cert-manager** — automated TLS certificates via Let's Encrypt (Cloudflare DNS challenge)
