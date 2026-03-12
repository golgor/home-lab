# cert-manager

## What is it?

cert-manager is the application that automatically obtains and renews TLS certificates — the things that make the padlock appear in your browser.

Left to itself, Traefik (the web gateway) would use a self-signed certificate: one it made up itself, not verified by anyone. Browsers don't trust those and show a security warning. cert-manager fixes this by getting a *real* certificate from **Let's Encrypt**, a free and widely trusted Certificate Authority.

See [Certificates & HTTPS](../concepts/certificates-https.md) for a full explanation of how certificates and HTTPS work.

## Why is it here?

Every service exposed over HTTPS needs a trusted certificate. Without cert-manager, you'd have to manually request certificates, download them, configure them in Traefik, and remember to renew them before they expire (Let's Encrypt certificates last 90 days).

cert-manager does all of that automatically.

## How is it configured?

cert-manager is deployed as a vendor app from `applications/vendor/cert-manager/`. The key pieces:

**`ClusterIssuer`** — defines *how* to get certificates. This home lab uses:
- Let's Encrypt production endpoint (real, trusted certificates)
- DNS-01 challenge via Cloudflare API (proves domain ownership by adding a DNS record)

**Cloudflare API token** — stored as a SealedSecret so it can live safely in Git. cert-manager uses it to create temporary DNS records during certificate issuance.

**`Certificate`** — defined in `applications/vendor/traefik-certs/`, requests a wildcard certificate for `*.neustrom.net`. This single certificate covers all subdomains, so you never need to configure certificates per service.

## Automatic renewal

cert-manager watches certificate expiry and renews automatically ~30 days before the certificate expires. No manual intervention needed.
