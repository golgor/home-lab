# Troubleshooting

## ArgoCD

### CRD Too Large for `kubectl apply`

```
The CustomResourceDefinition is invalid: metadata.annotations: Too long
```

Use server-side apply:

```bash
kustomize build applications/bootstrap/argocd/ --enable-helm \
  | kubectl apply --server-side --force-conflicts -f -
```

### Getting the Admin Password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

## Ingress / DNS

### Service Not Reachable via Hostname

1. Verify DNS resolves to the node IP: `nslookup argocd.home-lab.local`
2. Check the ingress exists: `kubectl get ingress -A`
3. Check Traefik logs: `kubectl logs -n kube-system -l app.kubernetes.io/name=traefik`
