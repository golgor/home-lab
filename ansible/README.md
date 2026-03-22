# Ansible

Ansible is a tool for automating tasks on remote machines. Instead of manually SSHing into each server and running commands, you write playbooks (YAML files) that describe what should be done, and Ansible handles the rest.

## How it works

Ansible connects to remote machines over SSH and runs commands on your behalf. No agent or special software needs to be installed on the remote machine — just SSH access is enough.

## Inventory

The `inventory.yaml` file tells Ansible which machines to connect to and how.

```yaml
myhosts:
  hosts:
    dietpi:
      ansible_host: 10.0.0.110
      ansible_user: dietpi
```

- `myhosts` — a group name, used to target multiple machines at once
- `ansible_host` — the IP address of the remote machine
- `ansible_user` — the SSH user to log in as

## SSH Key Authentication

Ansible connects via SSH. Rather than typing a password every time, we use SSH key authentication:

- **Your machine** has a private key (kept secret, never shared)
- **The remote machine** has your public key stored in `~/.ssh/authorized_keys`

When Ansible connects, SSH verifies the keys match — no password needed.

### First-time setup

**1. Generate an SSH key** (skip if you already have one at `~/.ssh/id_ed25519`):

```bash
ssh-keygen -t ed25519
```

**2. Copy your public key to the RPi:**

```bash
ssh-copy-id dietpi@10.0.0.110
```

This logs in with a password once and installs your public key on the remote machine so future logins are passwordless.

**3. Clear any stale host entry** (needed if the RPi was reinstalled):

```bash
ssh-keygen -R 10.0.0.110
```

Then accept the new host key:

```bash
ssh-keyscan -H 10.0.0.110 >> ~/.ssh/known_hosts
```

> **What is `known_hosts`?** When you first connect to a machine, SSH saves a fingerprint of that machine in `~/.ssh/known_hosts`. On future connections it checks the fingerprint still matches — this protects against connecting to an impostor. If you reinstall the RPi, it gets a new fingerprint and you need to remove the old entry first.

## Running commands

Test that everything is working with a ping:

```bash
uv run ansible myhosts -m ping -i inventory.yaml
```

A successful response looks like:

```
10.0.0.110 | SUCCESS => {
    "ping": "pong"
}
```

## Playbook

The playbook (`playbook.yaml`) provisions the RPi as a combined k3s + PostgreSQL host. This is the main server for the home lab — it runs a k3s cluster for hosting applications, and a local PostgreSQL instance that those applications use as their database.

Run it with:

```bash
uv run ansible-playbook -i inventory.yaml playbook.yaml
```

The playbook is idempotent — it is safe to run multiple times. Ansible checks the current state before making changes and only acts if something differs from what is described.

### Play 1: Update and upgrade packages

Runs `apt update && apt full-upgrade` to keep the system up to date. Equivalent to logging in and running it manually, but automated.

### Play 2: Configure PostgreSQL

PostgreSQL is installed on the RPi via DietPi and serves as the shared database for all applications running in k3s. Rather than each app managing its own database container, a single PostgreSQL instance on the host serves all of them. Database users and permissions are managed separately via Pulumi (see `infrastructure/`).

By default, PostgreSQL only accepts connections from the same machine (localhost). Two changes are needed to allow k3s workloads to connect over the network:

**1. Listen on all interfaces**

PostgreSQL is configured to accept connections on all network interfaces, not just localhost. This is done by dropping a config file into `/etc/postgresql/17/main/conf.d/01ansible.conf`:

```
listen_addresses = '*'
```

DietPi stores its own PostgreSQL settings in `conf.d/00dietpi.conf`. Using a separate file (`01ansible.conf`) avoids editing DietPi-managed files directly and keeps our changes clearly separated.

**2. Allow remote connections in `pg_hba.conf`**

`pg_hba.conf` (Host-Based Authentication) is PostgreSQL's access control file — it defines who is allowed to connect and how they must authenticate. By default only local connections are permitted.

The playbook appends a rule to allow any user on the local network (`10.0.0.0/24`) to connect using a password:

```
host    all    all    10.0.0.0/24    scram-sha-256
```

`scram-sha-256` is a secure password authentication method — credentials are never sent in plain text.

PostgreSQL is restarted automatically if either of these files changed, but only then.

> **Before running this play:** make sure you have set a password for the `postgres` superuser (or whichever user you intend to connect as), otherwise password authentication has nothing to verify against:
> ```bash
> ssh dietpi@10.0.0.110
> sudo -u postgres psql
> \password postgres
> ```

### Play 3: Configure k3s

Copies `diet-pi/k3s-config.yaml` to `/etc/rancher/k3s/config.yaml` on the RPi. K3s reads this file on startup to configure the node. The config disables the built-in Traefik ingress controller (we deploy our own via ArgoCD) and sets the kubeconfig file permissions so it can be read without root.

The `/etc/rancher/k3s/` directory is created if it does not already exist.
