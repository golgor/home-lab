# Home lab

The vocabulary for this home lab: one household's self-hosted services, the machines they run on, and the way Robert
and agents share the work. Implementation details live in the docs and ADRs, not here.

## Language

### Services and people

**Household service**:
A service that someone in the household relies on in everyday life, such as a recipe database or a baby sleep
tracker. It gets uptime and backup guarantees.
_Avoid_: Production app, core app

**Experiment**:
A service Robert is trying out to see if it fits. It is isolated from household services and has no backup promise.
_Avoid_: Test app, playground, sandbox

**Household member**:
A person in the household who uses services but does not operate the lab. Today that is Robert's wife.
_Avoid_: User, end user, family account

**Admin**:
The person who operates the lab and holds every human gate. Today that is only Robert.
_Avoid_: Owner, operator, root user

### Access

**Public app**:
Any service with an ingress. It is reachable from the internet through the tunnel and always has an IdP gate.
_Avoid_: Exposed app, external app

**Admin surface**:
Any interface that controls the lab itself, such as the Proxmox UI, the Talos and Kubernetes APIs, ArgoCD, the
Authentik admin interface or the Traefik dashboard. It is always LAN-only.
_Avoid_: Admin UI, dashboard, console

**LAN-only**:
Reachable from the home network and from nowhere else, not even through the tunnel behind the IdP.
_Avoid_: Internal, private

**IdP gate**:
The IdP standing between a public app and its visitors, either in front of the app at the proxy or as the app's own
login against the IdP.
_Avoid_: Auth layer, login wall

**Tunnel**:
The outbound connection from the home network to Cloudflare that carries household members' traffic to public apps.
_Avoid_: VPN, port forward

**IdP**:
The identity provider, Authentik, that holds household accounts and decides who may use which public app.
_Avoid_: SSO, auth server, login service

### Machines

**Host**:
The physical mini PC running Proxmox. Changes to it are a human gate.
_Avoid_: Server, node, hypervisor box

**Cluster VM**:
The Talos virtual machine on the host that runs the single-node Kubernetes cluster.
_Avoid_: Node, k8s box

**Home Assistant VM**:
The virtual machine on the host that runs Home Assistant with direct access to USB and radio hardware.
_Avoid_: HA box, smart home server

**Rebuild**:
Recreating the cluster VM and everything in it from git plus the secrets store, with no state carried over by hand.
_Avoid_: Reinstall, migration, restore

**Off-box backup**:
A copy of lab data stored somewhere other than the host. The disk mirror is not an off-box backup.
_Avoid_: RAID, snapshot, replica

### Secrets

**Secret value**:
The actual content of a secret, such as a password or token. Only the admin creates, reads or rotates one.
_Avoid_: Credential, key

**Secret reference**:
The name of a secret as it appears in git. Agents may write secret references but never see secret values.
_Avoid_: Sealed secret, encrypted secret

**Secrets store**:
The Bitwarden Secrets Manager organization "Neustrom", which holds every secret value for the lab. It is separate from
the household password vault.
_Avoid_: Vault, password manager

**Bootstrap secret**:
The one secret value placed into the cluster by hand so that it can read every other secret value from the secrets
store.
_Avoid_: Root secret, master key

**Secrets bundle**:
The Talos cluster's own certificate authority and keys, kept in the secrets store. Every Talos and Kubernetes client
config can be regenerated from it.
_Avoid_: talosconfig, cluster secrets

### Working with agents

**Infra bot**:
The dedicated agent that owns this repo's issues and pull requests and works through them with Robert.
_Avoid_: Bot, automation, CI

**Human gate**:
An action only the admin may take or approve, such as merging to `main`, applying infrastructure changes, handling a
secret value, deleting data or changing the host.
_Avoid_: Manual step, approval

**owner:human issue**:
An issue only Robert, the human admin, can complete, such as buying hardware, adding a secret value or making a
decision. Labelled `owner:human`.
_Avoid_: Manual task, blocker

**owner:agent issue**:
An issue the infra bot can complete through a pull request. Labelled `owner:agent`.
_Avoid_: Automated task, bot task

**Blocked issue**:
An issue that cannot start until another issue it is linked to is closed. Labelled `blocked`, with the blockers listed
under _Blocked by_ in its body.
_Avoid_: On hold, waiting

**Weekly digest**:
The infra bot's weekly summary of owner:human issues that are holding up other work.
_Avoid_: Report, status update
