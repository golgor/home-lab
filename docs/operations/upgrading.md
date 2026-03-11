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

## Upgrading k3s

TODO: Document k3s upgrade process.
