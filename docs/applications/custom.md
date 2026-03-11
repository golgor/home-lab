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

The ApplicationSet automatically discovers directories under
`applications/custom/` and creates an ArgoCD Application for each one.

## Adding a Custom App

1. Create a directory under `applications/custom/<app-name>/`
2. Add Kustomize manifests (deployment, service, ingress, etc.)
3. Reference the container image from ghcr.io
4. Commit and push — the ApplicationSet discovers it automatically

No `application.yaml` needed — the ApplicationSet handles that.

## Example Structure

```
applications/custom/my-app/
├── kustomization.yaml
├── deployment.yaml
├── service.yaml
└── ingress.yaml
```

## Image Updates

Because all custom apps use ghcr.io, ArgoCD Image Updater can be configured
once to monitor that registry and automatically update image tags across all
custom apps.
