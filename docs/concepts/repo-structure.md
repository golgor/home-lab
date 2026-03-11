# Repository Structure

This mono-repo organizes everything needed to run the home lab.

```
home-lab/
├── ansible/                  # Server provisioning playbooks
├── applications/
│   ├── bootstrap/            # Manually applied (pre-ArgoCD)
│   │   └── argocd/           # ArgoCD Helm + Kustomize
│   ├── vendor/               # Third-party apps managed by ArgoCD
│   └── custom/               # Self-developed apps managed by ArgoCD
├── infrastructure/           # Cluster-level infrastructure
├── docs/                     # This documentation (MkDocs)
└── mkdocs.yml
```

## Directory Conventions

| Directory | Managed By | Purpose |
|-----------|-----------|---------|
| `applications/bootstrap/` | `kubectl` (manual) | Components that must exist before ArgoCD |
| `applications/vendor/` | ArgoCD | Third-party applications (Grafana, etc.) |
| `applications/custom/` | ArgoCD | Your own applications |
| `infrastructure/` | ArgoCD | Cluster-wide resources (namespaces, RBAC, etc.) |
| `ansible/` | Ansible | Node provisioning and OS-level config |
