# Bootstrap

ArgoCD manages all application deployments via GitOps. However, ArgoCD itself
cannot deploy itself — it needs to be bootstrapped manually. This is the only
component that is applied directly with `kubectl`.

## Deploying ArgoCD

```bash
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -
```

!!! note "Why `--server-side --force-conflicts`?"
    The ArgoCD CRDs exceed the 262KB annotation limit imposed by client-side
    `kubectl apply`. Server-side apply avoids this limitation by not storing
    the `last-applied-configuration` annotation.

## Getting the Admin Password

After deployment, retrieve the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

The ArgoCD UI is available at [https://argocd.home-lab.local](https://argocd.home-lab.local)
(requires DNS — see [DNS & Ingress](dns-ingress.md)).

## What Gets Deployed

The bootstrap Kustomization at `applications/bootstrap/argocd/` deploys:

- ArgoCD Helm chart (version defined in `kustomization.yaml`)
- The `argocd` namespace
- A Traefik Ingress for `argocd.home-lab.local`
