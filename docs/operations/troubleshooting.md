# Troubleshooting

## ArgoCD

### CRD Too Large for `kubectl apply`

```text
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

## Traefik / Ingress

### Check Traefik logs

Traefik runs in the `traefik` namespace. Access logs filter to 400-599 status codes only.

```bash
kubectl logs -n traefik -l app.kubernetes.io/name=traefik
```

### Service not reachable via hostname

1. Verify DNS resolves to the node IP: `nslookup my-app.neustrom.net`
2. Check the route exists:

   ```bash
   kubectl get httproute -A
   kubectl get ingress -A
   ```

3. Check Traefik logs (see above)
4. Verify the Gateway is ready: `kubectl get gateway -n traefik`

### HTTPRoute stuck in sync loop (ArgoCD)

ArgoCD detects drift when `group`/`kind` fields are omitted from `parentRefs` or `backendRefs` —
Traefik fills them in and ArgoCD sees a diff. Always include them explicitly:

```yaml
parentRefs:
  - group: gateway.networking.k8s.io
    kind: Gateway
    name: traefik-gateway
    namespace: traefik
    sectionName: websecure

backendRefs:
  - group: ""
    kind: Service
    name: my-app
    port: 8080
    weight: 1
```

### Traefik middleware not applied cross-namespace

The `kubernetesCRD` provider requires `allowCrossNamespace: true` in `values.yaml` for a `Middleware` in
one namespace to reference a `Service` in another. Without it, the middleware silently fails.

### Gateway name

The Gateway created by the Traefik Helm chart is named `traefik-gateway` (not `traefik`). Verify with:

```bash
kubectl get gateway -n traefik
```

## cert-manager

### Certificate not issuing

```bash
kubectl describe certificate -n traefik neustrom-net-wildcard
kubectl describe certificaterequest -n traefik
kubectl logs -n cert-manager -l app=cert-manager
```

Common cause: Cloudflare API token `SealedSecret` not applied or kubeseal cert is stale.
Re-seal and re-apply after `mise run fetch-cert`.
