# Kustomize & Helm

This project uses **Kustomize** as the primary tool for managing Kubernetes
manifests, with **Helm** used to pull third-party charts.

## Why Kustomize?

- Native Kubernetes tooling — no templating language to learn
- Overlay-based — keeps base manifests clean
- ArgoCD has first-class Kustomize support

## Helm via Kustomize

Rather than using Helm directly, Helm charts are referenced in
`kustomization.yaml` using the `helmCharts` field:

```yaml
helmCharts:
  - name: argo-cd
    repo: https://argoproj.github.io/argo-helm
    version: "9.4.10"
    releaseName: argocd
    namespace: argocd
    valuesFile: values.yaml
```

This renders the Helm chart at build time, producing plain manifests that
Kustomize can further patch or overlay.

!!! info
    The `helmCharts` field requires standalone `kustomize` with the
    `--enable-helm` flag. It is **not** supported by `kubectl apply -k`.
