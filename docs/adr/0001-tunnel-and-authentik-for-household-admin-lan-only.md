---
status: accepted
date: 2026-10-11
---

# Cloudflare Tunnel and Authentik for household apps, admin surfaces on the LAN only

The ISP gives no static IP, so nothing can be port-forwarded. Since `5e9631d` the lab has been Tailscale-only, which
asks Robert's wife to run a Tailscale client and custom DNS settings. We decided that household members reach public
apps through a Cloudflare Tunnel on `neustrom.net`. Every public app has an IdP gate, either Authentik forward-auth at
the proxy or the app's own OIDC login against Authentik. Admin surfaces are reachable from the home LAN only and never
through the tunnel, even behind Authentik, because a flaw in the login layer would then expose the lab's control
planes. The target has no Tailscale.

## Considered options

- Tailscale only (the current setup). Nothing is reachable from the internet, but every household member and every
  future relative must join the tailnet. Rejected because access has to work for people who will not manage a VPN
  client.
- Admin surfaces through the tunnel behind Authentik. Convenient from anywhere, but one bug or misconfiguration in
  Authentik or the tunnel would put ArgoCD, the Kubernetes API or Proxmox on the internet. Rejected.
- Tailscale for the admin next to the tunnel. Rejected for now because remote admin is not needed yet. Adding it later
  is a small change and needs its own ADR.
- Tunnel with Cloudflare Access as the only gate. Less to run, but Robert knows Authentik from work, and Authentik also
  gives the apps themselves OIDC logins. Not chosen as the IdP. Adding Access as an extra layer later stays possible.
- A per-app allowlist for the tunnel, with private as the default. Rejected in favour of "an ingress means public", so
  that one setting, the ingress, decides exposure.
- Port forwarding or a self-hosted WireGuard server. Not possible without a static IP, and it opens the home router.

## Consequences

- Admin surfaces are the Proxmox UI, the Talos API, the Kubernetes API, ArgoCD, the Authentik admin interface and the
  Traefik dashboard. None of them gets a public ingress or a tunnel route.
- Robert can administer the lab only from home. Remote admin means adding Tailscale back through a new ADR.
- The IdP is the main control between personal data and the internet. An app that reaches the tunnel without an IdP
  gate is an exposure, so CI should fail a public route that has neither forward-auth nor an explicit annotation that
  marks it as using app-native OIDC against Authentik.
- Experiments are public too once they have an ingress, so they need an IdP gate like household services.
- Authentik's login flows must be public while its admin interface must not, so the public route has to block the
  admin paths.
- Home Assistant is the first app-native case. It logs in through `hass-oidc-auth` against Authentik with no
  proxy-level auth in front, because the mobile app cannot follow a forward-auth redirect. The mobile app logs in with
  a device code confirmed in a browser. See [ADR 0003](0003-proxmox-host-talos-vm-separate-ha-vm.md).
- The public `*.neustrom.net` record that points at the tailnet IP today goes away. Public hostnames point at the
  tunnel, and admin hostnames need a LAN-only way to resolve.
- Authentik moves from "disabled, files kept" to a household service, with its own backups.
- The stale branch `claude/secure-homelab-cloudflare-BX8c8` plans a tunnel too, but it predates this decision and is
  not the plan.
