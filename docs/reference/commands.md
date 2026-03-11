# Commands

## Bootstrap

```bash
# Deploy/upgrade ArgoCD
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -

# Apply the App of Apps (only needed once)
kubectl apply -f applications/vendor/vendor-apps.yaml

# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

## Sealed Secrets

```bash
# Install kubeseal CLI
# https://github.com/bitnami-labs/sealed-secrets#kubeseal

# Seal a secret
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

## Documentation

```bash
# Serve docs locally with live reload
uvx --with mkdocs --with mkdocs-material --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs serve --livereload

# Build static docs
uvx --with mkdocs --with mkdocs-material --with mkdocs-kroki-plugin --with mkdocs-minify-plugin -- mkdocs build
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

# Check cert-manager status
kubectl get certificates -A
kubectl get clusterissuers
```
