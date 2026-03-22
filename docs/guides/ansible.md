# Ansible

Ansible automates provisioning of the RPi host. The playbook configures
PostgreSQL and deploys the k3s config. All Ansible files live in `ansible/`.

## First-time setup

### SSH key authentication

Ansible connects over SSH using key authentication — no password prompts during
playbook runs.

**1. Generate a key** (skip if `~/.ssh/id_ed25519` already exists):

```bash
ssh-keygen -t ed25519
```

**2. Install your public key on the RPi:**

```bash
ssh-copy-id dietpi@10.0.0.110
```

This connects once with a password and writes your public key to
`~/.ssh/authorized_keys` on the remote — all future connections are
passwordless.

**3. Clear a stale host entry** (needed after RPi reinstall):

```bash
ssh-keygen -R 10.0.0.110
ssh-keyscan -H 10.0.0.110 >> ~/.ssh/known_hosts
```

!!! note
    SSH saves a fingerprint of each host in `~/.ssh/known_hosts`. On reinstall
    the RPi gets a new host key — the old entry must be removed first or SSH
    will refuse to connect.

### Verify connectivity

```bash
uv run ansible myhosts -m ping -i ansible/inventory.yaml
```

Expected output:

```text
dietpi | SUCCESS => {
    "ping": "pong"
}
```

## Inventory

`ansible/inventory.yaml` defines the hosts Ansible targets:

```yaml
myhosts:
  hosts:
    dietpi:
      ansible_host: 10.0.0.110
      ansible_user: dietpi
```

## Running the playbook

```bash
uv run ansible-playbook -i ansible/inventory.yaml ansible/playbook.yaml
```

The playbook is idempotent — safe to re-run at any time. Ansible checks
current state and only acts where something differs.

## What the playbook does

### Play 1 — System update

Runs `apt update && apt full-upgrade`. No configuration, just keeps the system
current.

### Play 2 — PostgreSQL

PostgreSQL is installed on the RPi via DietPi and acts as the shared database
for all k3s workloads. Database users and permissions are managed by Pulumi
(see [Database Management](pulumi/database.md)).

Out of the box, PostgreSQL only accepts local connections. Two changes are
needed:

#### Listen on all interfaces

A config file is dropped into `/etc/postgresql/17/main/conf.d/01ansible.conf`:

```ini
listen_addresses = '*'
```

DietPi owns `conf.d/00dietpi.conf` — using a separate numbered file avoids
touching DietPi-managed config and makes the override explicit.

#### Allow remote connections

The following rule is appended to `pg_hba.conf`:

```text
host    all    all    10.0.0.0/24    scram-sha-256
```

This permits password-authenticated connections from any host on the local
network. `scram-sha-256` hashes credentials in transit — passwords are never
sent in plain text.

PostgreSQL is restarted automatically if either file changed, and only then.

!!! warning
    Before running this play for the first time, set a password for the
    `postgres` superuser — otherwise password auth has nothing to verify against.

```bash
ssh dietpi@10.0.0.110
sudo -u postgres psql
\password postgres
```

### Play 3 — k3s config

Creates `/etc/rancher/k3s/` if absent, then copies `diet-pi/k3s-config.yaml`
to `/etc/rancher/k3s/config.yaml`. K3s reads this file on startup.

The config currently:

- Disables the built-in Traefik (we deploy our own via ArgoCD)
- Sets kubeconfig permissions to `644` so it is readable without root
- Adds `10.0.0.110` to the API server TLS SANs (required for remote `kubectl`
  access — see [Remote kubectl Access](k3s-remote-access.md))
