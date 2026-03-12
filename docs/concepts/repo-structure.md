# Repository Structure

This mono-repo organizes everything needed to run the home lab.

```text
home-lab/
├── ansible/                          # Server provisioning playbooks
├── applications/
│   ├── bootstrap/                    # Manually applied (pre-ArgoCD)
│   │   └── argocd/                   # ArgoCD Helm + Kustomize
│   ├── vendor/                       # Third-party apps managed by ArgoCD
│   │   ├── vendor-apps.yaml          # App of Apps (scans **/application.yaml)
│   │   ├── sealed-secrets/           # Bitnami Sealed Secrets
│   │   └── cert-manager/             # TLS certs via Let's Encrypt
│   └── custom/                       # Self-developed apps managed by ArgoCD
├── infrastructure/                   # Cluster-level infrastructure
├── docs/                             # This documentation (MkDocs)
└── mkdocs.yml
```

## Directory Conventions

| Directory | Managed By | Purpose |
| ----------- | ----------- | --------- |
| `applications/bootstrap/` | `kubectl` (manual) | Components that must exist before ArgoCD |
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
