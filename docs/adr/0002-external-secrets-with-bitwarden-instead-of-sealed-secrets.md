---
status: accepted
date: 2026-10-11
---

# External Secrets Operator with Bitwarden Secrets Manager instead of Sealed Secrets

Sealed Secrets ties every secret in git to one private key inside the cluster. That key has no backup, so a rebuild
means re-sealing every secret from plaintext. We decided to keep secret values in Bitwarden Secrets Manager and have
External Secrets Operator (ESO) pull them into the cluster. Git holds only `ExternalSecret` manifests, which name a
secret and contain no value. Sealed Secrets goes away.

## Considered options

- Keep Sealed Secrets and back up its key. Rebuilds still depend on that one key, and the sealing flow puts plaintext
  in a human's terminal on the way to git.
- SOPS with age keys in git. It works without a cluster-side store, but the age key becomes the new single point of
  loss and agents would still handle encrypted files directly.
- Another ESO backend, such as a self-hosted Vault or a cloud secret manager. More to run, or a new vendor, while the
  household already uses Bitwarden.

## Consequences

- Secret values live in a separate free Bitwarden organization, "Neustrom", with Secrets Manager enabled. The
  household's Families organization, "Nyström", cannot add Secrets Manager and keeps holding personal
  passwords. The free tier allows 2 users, 3 projects and 3 machine accounts.
- ESO's Bitwarden provider needs the `bitwarden-sdk-server` component in the cluster.
- One machine-account token is the only bootstrap secret, placed into the cluster by hand. A machine account with read
  access to the lab project is enough.
- Agents write `ExternalSecret` manifests and never create or read values. Adding or rotating a value is a human gate,
  and it is the one manual step left in an agent-managed lab. An issue that needs a new value is an `owner:robert`
  issue that blocks the agent's pull request.
- `fnox` is out of scope for now and keeps using the Nyström organization.
- The Talos secrets bundle and the OpenTofu state encryption key live in the same secrets store. See
  [ADR 0004](0004-opentofu-for-infrastructure-replacing-pulumi-argocd-for-apps.md).
