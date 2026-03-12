# Docs Writing Guide

Documentation for this home lab is written for two distinct personas. Every page should be written with one primary persona in mind.

## Personas

### Persona 1 — Future Me

**Who:** The owner of this cluster, returning after months away to migrate, debug, or extend it.

**Background:**
- Understands Kubernetes, GitOps, Helm, and Kustomize conceptually
- Has forgotten the specific decisions made in *this* cluster
- Comfortable with the terminal and kubectl

**Goals:**
- Migrate the cluster to a new machine (e.g. Raspberry Pi)
- Add a new service or troubleshoot a broken one
- Remember why something was done a certain way

**Writing style:**
- Terse and technical — no hand-holding
- Lead with commands, follow with explanation
- Always document the *why* behind non-obvious decisions
- Use admonitions for warnings about destructive or irreversible actions

---

### Persona 2 — Non-technical Friend

**Who:** Someone comfortable with code (CSS, JavaScript, Git) but with no infrastructure or cloud experience.

**Background:**
- Understands files, code, and version control
- Has never worked with servers, containers, or Kubernetes
- Does not know what a pod, namespace, ingress, or Helm chart is

**Goals:**
- Understand what this home lab is and what it runs
- Grasp the big picture without needing to operate the cluster
- Potentially self-host something simple in the future

**Writing style:**
- Friendly and incremental — build concepts before showing examples
- Use analogies (e.g. "Kubernetes is like a supervisor that restarts apps if they crash")
- Define jargon inline on first use, avoid it where possible
- Diagrams and visuals are welcome

---

## Section → Persona Mapping

| Section | Primary Persona | Rationale |
| --- | --- | --- |
| `concepts/` | Persona 2 | Explains what GitOps, Kustomize, Helm, ingress *are* — no assumed knowledge |
| `applications/` | Persona 2 | What's running and why — focus on purpose, not implementation |
| `guides/` | Persona 1 | How-to instructions for adding/changing apps — assumes cluster knowledge |
| `get-started/` | Persona 1 | Bootstrap and cluster setup — operational, command-heavy |
| `operations/` | Persona 1 | Migrations, troubleshooting, upgrades — assumes cluster knowledge |
| `reference/` | Persona 1 | Command cheatsheet and quick lookups |

## General Guidelines

- **One primary persona per page** — don't try to serve both at once
- **Mermaid diagrams** are supported and encouraged for architecture and flow explanations
- Pages are registered in `mkdocs.yml` under `nav:` — add new pages there
- Preview with `mise run docs`
