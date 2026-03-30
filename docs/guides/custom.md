# Custom Apps

Custom apps are applications you develop yourself. The source code and container
images live in separate GitHub repositories, while the deployment manifests live
here. All custom app images are hosted on GitHub Container Registry (ghcr.io).

## ApplicationSet

Unlike vendor apps (which use the App of Apps pattern with individual
`application.yaml` files), custom apps use an **ApplicationSet** with a Git
generator. This works well because all custom apps follow the same pattern:

- Same image registry (ghcr.io)
- Same repo for manifests (this repo)
- Same deployment conventions

The ApplicationSet (`applications/custom/custom-apps.yaml`) automatically
discovers directories under `applications/custom/` and creates an ArgoCD
Application for each one. Each app gets its own namespace matching the
directory name.

### Bootstrap (one-time)

The ApplicationSet must be applied manually once:

```bash
kubectl apply -f applications/custom/custom-apps.yaml
```

After that, adding a new directory under `applications/custom/` is enough
for ArgoCD to pick it up automatically.

## Adding a Custom App

1. Create a directory under `applications/custom/<app-name>/`
2. Add Kustomize manifests (deployment, service, ingress, etc.)
3. Reference the container image from ghcr.io
4. If the app needs a database, add a `PostgresqlServiceAccount` in
   `infrastructure/__main__.py` and run `pulumi up`
5. Seal any secrets with `mise run seal-secret`
6. Commit and push — the ApplicationSet discovers it automatically

No `application.yaml` needed — the ApplicationSet handles that.

## Example: cost-tracker

The `cost-tracker` app is the first custom app deployed this way:

```text
applications/custom/cost-tracker/
├── kustomization.yaml
├── deployment.yaml
├── service.yaml
└── ingressroute.yaml
```

- **kustomization.yaml** — sets namespace, lists resources, generates a
  ConfigMap for non-secret config (`LOG_LEVEL`, `ENV`)
- **deployment.yaml** — references `ghcr.io/golgor/cost-tracker:1.0.0`,
  injects secrets from a SealedSecret and config from the ConfigMap
- **service.yaml** — ClusterIP service on port 8000
- **ingressroute.yaml** — Traefik IngressRoute for `costs.neustrom.net`

## Image Updates

Because all custom apps use ghcr.io, ArgoCD Image Updater can be configured
once to monitor that registry and automatically update image tags across all
custom apps.
