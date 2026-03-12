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
# Fetch cluster public cert (run after cluster re-install)
mise run fetch-cert

# Seal a secret interactively from a .env file
mise run seal-secret

# Seal manually
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

## Documentation

```bash
# Serve docs locally with live reload
mise run docs
```

## Linting

```bash
# Lint YAML and validate Kubernetes manifests
mise run lint
```

Runs:

- `yamllint` — YAML syntax and style
- `kubeconform` — Kubernetes manifest schema validation
- `check-jsonschema` — Helm values schema validation (Traefik, cert-manager)

## Cluster

```bash
# Check node status
kubectl get nodes

# Check all pods
kubectl get pods -A

# Check ArgoCD status
kubectl get pods -n argocd

# Check Traefik logs (errors only — access log filters to 400-599)
kubectl logs -n traefik -l app.kubernetes.io/name=traefik

# Check ingress/routing resources
kubectl get ingress -A
kubectl get httproute -A
kubectl get ingressroute -A
kubectl get gateway -A

# Check cert-manager status
kubectl get certificates -A
kubectl get clusterissuers
```