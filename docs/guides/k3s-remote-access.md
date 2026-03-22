# Remote kubectl Access

How to configure `kubectl` on another machine to access the k3s cluster.

## Prerequisites

- k3s running on the remote host (`10.0.0.110`)
- SSH access to the remote host
- `kubectl` installed locally

## 1. Configure tls-san

By default k3s only includes `127.0.0.1` and `localhost` in its API server TLS
certificate SANs. Connecting from another machine via the node's IP will fail
with `x509: certificate signed by unknown authority` unless the IP is added.

Add `tls-san` to `diet-pi/k3s-config.yaml`:

```yaml
tls-san:
  - "10.0.0.110"
```

Deploy the updated config via Ansible, then force k3s to regenerate its TLS
certificate by deleting it and restarting:

```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbook.yaml

ssh dietpi@10.0.0.110 "sudo systemctl stop k3s \
  && sudo rm /var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt \
             /var/lib/rancher/k3s/server/tls/serving-kube-apiserver.key \
  && sudo systemctl start k3s"
```

!!! warning
    k3s only regenerates TLS certs if they are absent. A plain restart is not
    enough — the existing cert files must be deleted first.

Verify the new cert includes the IP:

```bash
ssh dietpi@10.0.0.110 "sudo openssl x509 \
  -in /var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt \
  -text -noout | grep -A2 'Subject Alternative'"
```

## 2. Copy and merge the kubeconfig

k3s writes a kubeconfig to `/etc/rancher/k3s/k3s.yaml` on the remote host.
It always contains `server: https://127.0.0.1:6443` — this must be corrected
before merging.

```bash
# Copy from remote
scp dietpi@10.0.0.110:/etc/rancher/k3s/k3s.yaml /tmp/k3s.yaml

# Fix the server address and rename context/cluster from 'default'
kubectl config set-cluster default --server=https://10.0.0.110:6443 --kubeconfig /tmp/k3s.yaml
kubectl config rename-context default homelab --kubeconfig /tmp/k3s.yaml

# Merge into local kubeconfig
KUBECONFIG=~/.kube/config:/tmp/k3s.yaml kubectl config view --flatten > /tmp/merged.yaml
mv /tmp/merged.yaml ~/.kube/config
```

!!! note
    The `--kubeconfig /tmp/k3s.yaml` flag scopes all changes to the temporary
    file, leaving your existing kubeconfig untouched until the final merge.

## 3. Verify

```bash
kubectl --context homelab get nodes
```

## Re-running after a cluster reinstall

k3s generates a new CA on reinstall, so the `certificate-authority-data` in
your local kubeconfig becomes stale. Remove the old entries and re-merge:

```bash
kubectl config delete-context homelab
kubectl config delete-cluster default
kubectl config delete-user default
```

Then repeat [step 2](#2-copy-and-merge-the-kubeconfig).
