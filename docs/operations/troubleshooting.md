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

## DNS / Pod Networking

### Pod can't resolve `*.neustrom.net`

**Symptom:** app returns 503, logs show connection errors to `auth.neustrom.net` or other cluster hostnames.

**Diagnose** from inside the cluster:

```bash
kubectl run tmp-shell --rm -i --tty --image=busybox -- nslookup auth.neustrom.net
```

If you see `NXDOMAIN`, the pod's DNS (CoreDNS) can't resolve the domain.

**Cause:** `*.neustrom.net` is only resolvable via PiHole. CoreDNS inherits the node's DNS
settings. If the RPi doesn't use PiHole as its DNS server, pods can't resolve those domains.

**Workaround:** add `hostAliases` to the pod spec:

```yaml
spec:
  hostAliases:
    - ip: "10.0.0.110"
      hostnames:
        - auth.neustrom.net
```

**Proper fix:** configure the RPi to use PiHole as its DNS server so all pods resolve
`*.neustrom.net` automatically.

## Container Images

### Image pull 401 Unauthorized from ghcr.io

```text
failed to authorize: failed to fetch anonymous token: unexpected status: 401 Unauthorized
```

**Cause:** GitHub Container Registry packages default to **private**, even when the source repo is public.

**Fix (preferred):** make the package public in GitHub → Package settings → Change visibility → Public.

**Fix (private image):** create a Kubernetes secret with a GitHub PAT and reference it as `imagePullSecrets`
in the pod spec.

## cert-manager

### Certificate not issuing

```bash
kubectl describe certificate -n traefik neustrom-net-wildcard
kubectl describe certificaterequest -n traefik
kubectl logs -n cert-manager -l app=cert-manager
```

Common cause: Cloudflare API token `SealedSecret` not applied or kubeseal cert is stale.
Re-seal and re-apply after `mise run fetch-cert`.
