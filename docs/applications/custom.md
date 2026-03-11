# Adding a Custom App

Custom apps are applications you develop yourself. The source code and container
images live in separate GitHub repositories, while the deployment manifests live
here.

## Steps

1. Create a directory under `applications/custom/<app-name>/`
2. Add Kustomize manifests (deployment, service, ingress, etc.)
3. Reference the container image from your GitHub Container Registry (or other registry)
4. Add an ArgoCD `Application` resource pointing to the directory
5. Commit and push — ArgoCD deploys it automatically

## Example Structure

```
applications/custom/my-app/
├── kustomization.yaml
├── deployment.yaml
├── service.yaml
└── ingress.yaml
```
