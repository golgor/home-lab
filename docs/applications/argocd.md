# ArgoCD

*Primary audience: Persona 2*

## What is it?

ArgoCD is the automation engine that keeps the cluster in sync with this Git repository.

Think of it like this: this repository is a blueprint. ArgoCD continuously reads that blueprint and makes sure the cluster matches it — if something drifts (a pod crashes, a config gets changed manually), ArgoCD corrects it. If you want to change something, you change the blueprint (Git), and ArgoCD does the rest.

This is the core of the **GitOps** pattern this home lab is built on. See [GitOps](../concepts/gitops.md) for a deeper explanation.

## Why is it here?

Without ArgoCD, deploying or updating any application would mean running `kubectl` commands manually. With ArgoCD, pushing to Git *is* the deployment. This means:

- Every change is tracked in Git history — you always know what changed and when
- Recovering from a broken cluster is a matter of re-applying the same repository
- No manual steps to forget or get wrong

## How is it configured?

ArgoCD is the one application that *cannot* manage itself — something has to be deployed before ArgoCD exists to deploy things. So it's bootstrapped manually once:

```bash
kustomize build --enable-helm applications/bootstrap/argocd \
  | kubectl apply --server-side --force-conflicts -f -
```

After that, all other applications are managed by ArgoCD.

Configuration lives in `applications/bootstrap/argocd/`. Key settings:

- **`server.insecure: true`** — ArgoCD doesn't handle its own TLS; Traefik does that at the front door
- **`kustomize.buildOptions: --enable-helm`** — allows Kustomize to inflate Helm charts, which is how vendor apps are deployed

## Accessing ArgoCD

ArgoCD is available at [https://argocd.neustrom.net](https://argocd.neustrom.net).

Since the cluster runs locally, you need to tell your machine where to find that address. Add this line to `/etc/hosts`:

```
127.0.0.1  argocd.neustrom.net
```

The default admin password can be retrieved with:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```
