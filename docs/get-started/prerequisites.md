# Prerequisites

## Hardware

TODO: Describe the hardware setup (nodes, specs, networking).

## Software

The following tools are required on your local machine:

- [kubectl](https://kubernetes.io/docs/tasks/tools/) — Kubernetes CLI
- [kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/) — Manifest management
  (standalone, for `--enable-helm` support)
- [Helm](https://helm.sh/docs/intro/install/) — Required by Kustomize for Helm chart rendering

## k3s

The cluster runs [k3s](https://k3s.io/), a lightweight Kubernetes distribution. k3s ships with:

- **Traefik** as the default ingress controller
- **CoreDNS** for cluster DNS
- **Local-path provisioner** for persistent volumes
