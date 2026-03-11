# Home Lab

Mono-repo for home lab infrastructure based on k3s.

## Structure

- `ansible/` - Ansible playbooks for server provisioning
- `applications/` - Application/service configurations
  - `bootstrap/argocd/` - ArgoCD (manually applied, not managed by ArgoCD)
  - `vendor/` - Third-party apps managed by ArgoCD (App of Apps pattern)
    - `vendor-apps.yaml` - App of Apps, scans for `**/application.yaml`
    - `sealed-secrets/` - Bitnami Sealed Secrets
    - `cert-manager/` - cert-manager + Let's Encrypt ClusterIssuer (Cloudflare DNS challenge)
  - `custom/` - Self-developed apps (separate repos, images on GitHub)
- `infrastructure/` - Infrastructure definitions
- `docs/` - MkDocs Material documentation site

## Commands

```bash
uvx --with mkdocs --with mkdocs-material --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs serve --livereload
uvx --with mkdocs --with mkdocs-material --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs build     # Build static docs site
```

## Docs

- Config: `mkdocs.yml` (Material theme, mermaid diagrams supported)
- Pages defined in `nav:` section of `mkdocs.yml`
- Add new pages to `docs/` and register in `mkdocs.yml` nav tree
