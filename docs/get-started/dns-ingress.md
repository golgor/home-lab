# DNS & Ingress

## How It Works

k3s ships with Traefik as the default ingress controller. When you create an
`Ingress` resource with a hostname, Traefik routes incoming traffic to the
correct service.

```
Browser → argocd.home-lab.local → (DNS) → Node IP → Traefik → Service
```

## Local DNS Setup

For `*.home-lab.local` domains to resolve to your k3s node, you need one of:

### Option 1: `/etc/hosts`

Add entries on each machine that needs access:

```
192.168.x.x  argocd.home-lab.local
```

### Option 2: Local DNS Server

If you run a local DNS server (Pi-hole, Adguard Home, etc.), add a wildcard
or individual DNS records pointing `*.home-lab.local` to your node IP.

## HTTP to HTTPS Redirect

Each ingress uses a Traefik `Middleware` to redirect HTTP traffic to HTTPS.
This ensures that navigating to `http://argocd.home-lab.local` automatically
redirects to `https://argocd.home-lab.local`.

## TLS

By default, Traefik serves a self-signed certificate. Your browser will show a
security warning — this is expected for a local setup.

For trusted certificates, you can later add [cert-manager](https://cert-manager.io/)
with a local CA or Let's Encrypt.
