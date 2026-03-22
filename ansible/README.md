# Ansible

Ansible is a tool for automating tasks on remote machines. Instead of manually SSHing into each server and running commands, you write playbooks (YAML files) that describe what should be done, and Ansible handles the rest.

## How it works

Ansible connects to remote machines over SSH and runs commands on your behalf. No agent or special software needs to be installed on the remote machine — just SSH access is enough.

## Inventory

The `inventory.ini` file tells Ansible which machines to connect to and how.

```ini
[myhosts]
10.0.0.110 ansible_user=dietpi
```

- `[myhosts]` — a group name, used to target multiple machines at once
- `10.0.0.110` — the IP address of the remote machine
- `ansible_user=dietpi` — the SSH user to log in as

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
uv run ansible myhosts -m ping -i inventory.ini
```

A successful response looks like:

```
10.0.0.110 | SUCCESS => {
    "ping": "pong"
}
```
