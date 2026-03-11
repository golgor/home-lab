# Adding a Vendor App

Vendor apps are third-party applications deployed via Kustomize (optionally
wrapping a Helm chart).

## Steps

1. Create a directory under `applications/vendor/<app-name>/`
2. Add a `kustomization.yaml` (with `helmCharts` if using a Helm chart, or
   `resources` for plain manifests)
3. Add a `values.yaml` if using Helm
4. Add an ArgoCD `Application` resource pointing to the directory
5. Commit and push — ArgoCD picks it up automatically

## Example Structure

```
applications/vendor/grafana/
├── kustomization.yaml
├── values.yaml
└── ingress.yaml
```
