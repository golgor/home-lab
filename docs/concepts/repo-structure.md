# Repository Structure

This mono-repo organizes everything needed to run the home lab.

```text
home-lab/
├── ansible/                          # Server provisioning playbooks
├── applications/
│   ├── bootstrap/                    # Applied by hand to start a cluster
│   │   ├── argocd/                   # ArgoCD Helm + Kustomize
│   │   ├── projects.yaml             # AppProject apps (root and discovery stay in default)
│   │   └── root.yaml                 # Root app-of-apps (syncs itself, projects, vendor-apps, custom-apps)
│   ├── vendor/                       # Third-party apps managed by ArgoCD
│   │   ├── vendor-apps.yaml          # App of Apps (scans **/application.yaml)
│   │   ├── sealed-secrets/           # Bitnami Sealed Secrets
│   │   └── cert-manager/             # TLS certs via Let's Encrypt
│   └── custom/                       # Self-developed apps managed by ArgoCD
│       └── custom-apps.yaml          # ApplicationSet (one app per directory)
├── infrastructure/                   # Cluster-level infrastructure
├── docs/                             # This documentation (MkDocs)
└── mkdocs.yml
```

## Directory Conventions

| Directory | Managed By | Purpose |
| ----------- | ----------- | --------- |
| `applications/bootstrap/` | `kubectl` (manual) | What you apply by hand to start a cluster. The root app-of-apps then manages itself |
| `applications/vendor/` | ArgoCD (App of Apps) | Third-party applications |
| `applications/custom/` | ArgoCD | Your own applications |
| `infrastructure/` | ArgoCD | Cluster-wide resources (namespaces, RBAC, etc.) |
| `ansible/` | Ansible | Node provisioning and OS-level config |

## Vendor App Convention

Each vendor app lives in its own directory under `applications/vendor/` and contains:

| File | Purpose |
| ------ | --------- |
| `application.yaml` | ArgoCD Application resource (discovered by App of Apps) |
| `kustomization.yaml` | Kustomize manifest (may include `helmCharts`) |
| `values.yaml` | Helm values (if using a Helm chart) |
| Additional resources | Ingress, middleware, secrets, etc. |
