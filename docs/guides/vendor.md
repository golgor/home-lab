# Adding a Vendor App

Vendor apps are third-party applications deployed via Kustomize (optionally
wrapping a Helm chart). They are automatically discovered by the App of Apps.

## Steps

1. Create a directory under `applications/vendor/<app-name>/`
2. Add an `application.yaml` — ArgoCD Application resource pointing to this directory
3. Add a `kustomization.yaml` (with `helmCharts` if using a Helm chart, or
   `resources` for plain manifests)
4. Add a `values.yaml` if using Helm
5. Commit and push — ArgoCD picks it up automatically

## Example Structure

```text
applications/vendor/grafana/
├── application.yaml        # ArgoCD Application (discovered by App of Apps)
├── kustomization.yaml      # Kustomize with helmCharts
├── values.yaml             # Helm values
└── ingress.yaml            # Extra resources (optional)
```

## Example `application.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grafana
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/golgor/home-lab.git
    targetRevision: HEAD
    path: applications/vendor/grafana
  destination:
    server: https://kubernetes.default.svc
    namespace: grafana
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
  revisionHistoryLimit: 2
```

## Example `kustomization.yaml` (Helm chart)

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: grafana

resources:
  - ingress.yaml

helmCharts:
  - name: grafana
    repo: https://grafana.github.io/helm-charts
    version: "8.0.0"
    releaseName: grafana
    namespace: grafana
    valuesFile: values.yaml
```
