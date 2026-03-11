# Commands

## Bootstrap

```bash
# Deploy ArgoCD
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -

# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

## Documentation

```bash
# Serve docs locally with live reload
uvx --with mkdocs --with mkdocs-material --with mkdocs --with minify-html mkdocs serve --livereload

# Build static docs
uvx --with mkdocs --with mkdocs-material --with mkdocs --with minify-html mkdocs build
```

## Cluster

```bash
# Check node status
kubectl get nodes

# Check all pods
kubectl get pods -A

# Check ArgoCD status
kubectl get pods -n argocd

# Check ingress resources
kubectl get ingress -A
```
