# Home Lab

Mono-repo for home lab infrastructure based on k3s.

## Structure

- `ansible/` - Ansible playbooks for server provisioning
- `applications/` - Application/service configurations
  - `vendor/` - Third-party apps (e.g. Grafana, Pi-hole)
  - `custom/` - Self-developed apps (separate repos, images on GitHub)
- `infrastructure/` - Infrastructure definitions (Kustomize + Helm)
  - `argocd/` - ArgoCD deployment (Helm chart via Kustomize)
- `docs/` - MkDocs Material documentation site

## Commands

```bash
uvx --with mkdocs --with mkdocs-techdocs-core --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs serve --livereload
uvx --with mkdocs --with mkdocs-techdocs-core --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs build     # Build static docs site
```

## Docs

- Config: `mkdocs.yml` (Material theme, mermaid diagrams supported)
- Pages defined in `nav:` section of `mkdocs.yml`
- Add new pages to `docs/` and register in `mkdocs.yml` nav tree
