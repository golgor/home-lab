---
status: accepted
date: 2026-10-11
---

# Agents open pull requests, CI must pass, Robert merges

The lab is meant to be managed by agents, but ArgoCD deploys whatever lands on `main`, so merge access is cluster
access. We decided that agents open pull requests, CI must pass, and Robert merges. A dedicated infra bot owns the
repo's issues and pull requests, and the work queue makes explicit which steps are Robert's.

## Considered options

- Agents merge and deploy on their own within limits. This is the long-term goal, but Robert first wants to trust the
  quality of the agents' work and of the security reviews.
- Agents only suggest changes in chat. That keeps a human in the loop but loses the issue history and makes Robert
  the one who turns every suggestion into a change.

## Consequences

- `main` needs branch protection and required CI before an agent gets write access.
- Some actions stay human gates even after agents may merge: deleting data, adding or rotating secret values, and
  changing the Proxmox host.
- Issues are labelled `owner:robert` or `owner:agent`, plus `blocked` and `needs-decision` where they apply, with
  "blocked by" links and a GitHub Project board. The infra bot opens pull requests only for `owner:agent` issues that
  are not blocked.
- The infra bot posts a weekly digest of `owner:robert` issues that block other work, and pings Robert when one blocks
  an otherwise ready pull request.
- Letting agents merge low-risk changes, such as image bumps that pass CI and verification, needs a new ADR that
  supersedes this one.
