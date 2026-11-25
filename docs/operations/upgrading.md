# Upgrading

## Upgrading ArgoCD

1. Update the `version` field in `applications/bootstrap/argocd/kustomization.yaml`
2. Review the [ArgoCD changelog](https://github.com/argoproj/argo-cd/releases) for breaking changes
3. Re-apply the bootstrap:

```bash
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -
```

Notes:

- **Helm 4**: Argo CD >= 3.5 renders Helm charts with Helm 4. Locally, if `helm` is v4, you need
  `kustomize` >= 5.8.1, or `kustomize build --enable-helm` fails.
- **NetworkPolicies**: chart 10 creates NetworkPolicies for the Argo CD components by default. `kubectl apply`
  does not prune, so rolling back to chart 9 leaves them behind. Delete them by hand.
- **Immutable Job**: if the apply fails with an immutable-field error on the `argocd-redis-secret-init` Job,
  run `kubectl -n argocd delete job argocd-redis-secret-init` and re-apply.

## Upgrading Vendor Apps

Update the chart version in the app's `kustomization.yaml` and commit.
ArgoCD will sync the change automatically.

## Upgrading k3s

TODO: Document k3s upgrade process.
