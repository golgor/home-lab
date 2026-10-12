# Research: Home Assistant VM and its database

Status: research input, not a decision. Researched 2026-10-11. Robert's decisions based on it are in
[ADR 0003](../adr/0003-proxmox-host-talos-vm-separate-ha-vm.md).
Scope: how the Home Assistant (HA) VM on Proxmox VE 9 should be set up, whether HA should use Postgres, and if so
where.

## TL;DR (recommendation)

1. **Install method: Home Assistant OS (HAOS) VM.** It is the only method that has apps (formerly add-ons), one-click
   updates and the native backup system. HA Container is the only other supported method. Core and Supervised were
   deprecated in 2025.6 and lost support after 2025.12.
2. **Database: keep the default SQLite inside HAOS.** Tune it with recorder excludes, a sensible `purge_keep_days`, and
   rely on long-term statistics (kept forever) for history. Do not put HA's recorder on CloudNativePG (CNPG) in the
   Talos cluster. That creates a hard runtime dependency from the house's control plane on the cluster, history drops
   out of HA's own backups, and HA's docs say SQLite is the most tested and optimized engine.
3. **If long-term raw history is wanted later**, add a separate time-series store (InfluxDB or VictoriaMetrics) as a
   secondary sink, which can live in the cluster because HA keeps working if it is down.
4. **Backups.** HAOS native backups, encrypted, to the built-in Cloudflare R2 backup location (HA 2026.2+), plus
   Proxmox `vzdump` of the VM to the backup target.
5. **Exposure.** Cloudflare Tunnel to Traefik in the cluster, then a selectorless Service and EndpointSlice pointing at
   the HA VM IP. Set Trust X-Forwarded-For and Trusted proxies (now in the UI since 2026.8). Login via HA's own auth
   plus `hass-oidc-auth` with Authentik. No Cloudflare Access or Authentik forward-auth in front of HA, because the
   mobile app breaks.
6. **OpenTofu.** The HA VM, its disk import, and USB mappings can be declared with `bpg/proxmox`. Onboarding,
   integrations, HACS, OIDC config and the backup encryption key stay manual (or UI-driven).

## 1. Install method on Proxmox

### What is supported in 2026

- Supported: Home Assistant Operating System (recommended) and Home Assistant Container. Source: [HA
  installation docs](https://www.home-assistant.io/installation/)
- Deprecated: Core (Python venv) and Supervised, announced 2025-05-22, supported until 2025.12, unsupported after that
  (issues no longer accepted). Source: [HA blog, deprecating Core and
  Supervised](https://www.home-assistant.io/blog/2025/05/22/deprecating-core-and-supervised-installation-methods-and-32-bit-systems/)
- Since 2026.2, add-ons are called "apps". Terminology only. Source: [HA 2026.2 release
  notes](https://www.home-assistant.io/blog/2026/02/04/release-20262/#add-ons-are-now-called-apps)
- Container has no apps, and "some integrations, such as Thread and Z-Wave, are controlled by apps. There is no
  out-of-the-box support for these on Container installations." Source: [HA installation
  docs](https://www.home-assistant.io/installation/)

### Comparison

| | HAOS VM | HA Container (in a Debian VM or in the cluster) | Core / Supervised |
| --- | --- | --- | --- |
| Support status | Recommended | Supported | Unsupported since 2025.12 |
| Apps (Z2M, Mosquitto, OTBR/Thread, Matter server, ESPHome) | Yes, one click | No, run them yourself | n/a |
| Updates (OS + core + apps) | One click / automatic | Manual image bumps (Renovate could do it) | n/a |
| Native backups incl. apps | Yes | Config only, no apps | n/a |
| GitOps / declarative | Weak (UI driven, `/config` is files) | Strong | n/a |
| Hardware access | VM passthrough, simple | Device mapping, privileged, host networking | n/a |
| Ops burden | Lowest | Medium/high | n/a |

**Recommendation: HAOS VM.** The point of a separate HA VM is to give HA its own appliance-like life cycle next to the
cluster. HAOS does that, and Thread/Matter and Zigbee2MQTT come as apps. Running HA Container in Talos was
already ruled out (USB/Bluetooth/mDNS needs).

### VM shape (per HA docs for KVM)

From [HA Linux installation docs](https://www.home-assistant.io/installation/linux):

- Image: `haos_ova-<ver>.qcow2.xz` (KVM). Latest at time of writing: 18.3 (released 2026-09-17), [HAOS
  releases](https://github.com/home-assistant/operating-system/releases)
- Minimum 2 GB RAM, 2 vCPU. Suggest 4 GB / 2 to 4 vCPU and a 64 GB disk for a household with Zigbee2MQTT and a few apps.
- UEFI required, non-secure-boot OVMF. In Proxmox: `bios = ovmf`, EFI disk with `pre_enrolled_keys = false`, machine
  `q35`, `virtio-scsi` controller.
- QEMU guest agent channel (HAOS ships the agent).
- Network: bridge onto the LAN (`vmbr0`), not NAT. mDNS, SSDP, Matter and HomeKit discovery need the same L2 segment and
  IPv6 link-local. Give it a DHCP reservation.
- Since 2026.8 the HAOS default HTTP port is 80 (Container stays 8123). Check which port the fresh install uses
  before writing the EndpointSlice. Source: [HA HTTP integration](https://www.home-assistant.io/integrations/http/)

### OpenTofu with bpg/proxmox

Provider: `bpg/proxmox` v0.116.0 (2026-10-06). Notes from the provider docs in
[bpg/terraform-provider-proxmox](https://github.com/bpg/terraform-provider-proxmox):

- Many resources are being renamed from `proxmox_virtual_environment_*` to `proxmox_*` (the old names are deprecated,
  removal in v1.0). For example `proxmox_download_file`, `proxmox_hardware_mapping_usb`. The new `proxmox_vm` resource
  is marked experimental, do not use in production, so keep `proxmox_virtual_environment_vm` for the VM for now.
- `.qcow2.xz` cannot be decompressed as xz by Proxmox's download-url API. The provider's cloud-image guide documents
  using `decompression_algorithm = "zst"` (which handles xz), `content_type = "iso"`, a `.img` file name, and `file_id`
  (not `import_from`) on the disk. This path needs SSH configured in the provider. Source: `docs/guides/cloud-image.md`
  in the repo.
- USB passthrough: create a cluster resource mapping by `vendor:product` id (optionally pinned to a physical port
  `path`), then reference it from the VM's `usb { mapping = ... }`. Mapping by id survives re-plugging into another
  port. Proxmox reference: [Proxmox wiki, USB devices in
  VMs](https://pve.proxmox.com/wiki/USB_Devices_in_Virtual_Machines)

Sketch (not tested, values are placeholders):

```hcl
resource "proxmox_download_file" "haos" {
  node_name               = "pve"
  datastore_id            = "local"
  content_type            = "iso"
  url                     = "https://github.com/home-assistant/operating-system/releases/download/18.3/haos_ova-18.3.qcow2.xz"
  decompression_algorithm = "zst"            # Proxmox zst path also handles xz
  file_name               = "haos_ova-18.3.qcow2.img"
}

resource "proxmox_hardware_mapping_usb" "zigbee" {
  name = "zigbee-coordinator"
  map = [{
    node    = "pve"
    id      = "10c4:ea60"                    # example: CP210x-based stick, check with lsusb
    comment = "Zigbee coordinator"
  }]
}

resource "proxmox_virtual_environment_vm" "haos" {
  name      = "haos"
  node_name = "pve"
  vm_id     = 200
  bios      = "ovmf"
  machine   = "q35"
  on_boot   = true
  scsi_hardware = "virtio-scsi-single"

  agent { enabled = true }
  cpu {
    cores = 2
    type  = "host"
  }
  memory { dedicated = 4096 }

  efi_disk {
    datastore_id      = "local-zfs"
    type              = "4m"
    pre_enrolled_keys = false                # HAOS needs secure boot off
  }

  disk {
    datastore_id = "local-zfs"
    interface    = "scsi0"
    file_id      = proxmox_download_file.haos.id
    size         = 64
    discard      = "on"
    iothread     = true
  }

  network_device { bridge = "vmbr0" }

  usb {
    mapping = proxmox_hardware_mapping_usb.zigbee.name
    usb3    = false
  }

  startup { order = 2 }                      # after Talos VM if you want ordering

  lifecycle {
    # HAOS updates itself; after first boot the disk is HA's, not the image's.
    ignore_changes = [disk[0].file_id]
  }
}
```

**What stays manual.** Onboarding (owner account, location), adding integrations (ZHA or Zigbee2MQTT, Matter, Thread),
HACS install and `hass-oidc-auth`, HTTP proxy settings, storing the backup emergency kit, Bluetooth adapter choice.
`/config` can be versioned in git (a `git pull` app or Samba and a script), but HA is UI-first and most integration
config lives in `.storage/`, so treat HA as a pet with good backups, not as GitOps.

**Hardware tips.**

- A network (Ethernet/PoE) Zigbee coordinator (for example SMLIGHT SLZB-06/07 class) avoids USB passthrough
  and can sit centrally in the house. If USB, use a USB extension cable away from the mini PC (USB3 interference).
- **Bluetooth.** Pass a dedicated USB BT dongle, or better, use ESPHome Bluetooth proxies (ESP32) around the house.
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy/)
- **Thread/Matter.** HA's OpenThread Border Router and Matter Server run as apps on HAOS and need a Thread-capable radio
  (for example Home Assistant Connect ZBT-2 flashed for Thread). Matter needs IPv6 on the LAN. [HA Matter
  integration](https://www.home-assistant.io/integrations/matter/) and [HA Thread
  integration](https://www.home-assistant.io/integrations/thread/)

## 2. Recorder database

### What the recorder stores

From [HA recorder integration](https://www.home-assistant.io/integrations/recorder/):

- Every state change and event, used by History, Activity (logbook), dashboard graphs and statistics.
- Default engine SQLite, file `/config/home-assistant_v2.db`. "The default, and recommended, database engine is
  SQLite."
- Supported engines: MariaDB >= 10.3, MySQL >= 8.0, PostgreSQL >= 12, SQLite >= 3.40.1. MariaDB before 10.5.17 /
  10.6.9 / 10.7.5 / 10.8.4 has a known performance regression.
- Warning in the docs: "SQLite is the most tested, and newer version of Home Assistant are highly optimized to perform
  well when using SQLite. When choosing another option, you should be comfortable in the role of the database
  administrator, including making backups of the external database."
- "Changing database used by the recorder may result in losing your existing history. Migrating data is not supported."
  So decide before going live.
- Defaults: `purge_keep_days: 10`, nightly auto purge at 04:12, monthly auto repack, `commit_interval: 5`. Keep free
  disk >= DB size for schema migrations; with SQLite corruption recovery keep 2.5x.
- External DB connectivity knobs: `db_max_retries` (10) and `db_retry_wait` (3 s). After that the recorder gives up, so
  history is lost until restart.

### Long-term statistics

- Sensors with a `state_class` (`measurement`, `total`, `total_increasing`) get 5-minute short-term statistics and
  hourly long-term statistics (min/max/mean or sum). Source: [HA developer docs, long-term
  statistics](https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics)
- Long-term statistics are not purged by `purge_keep_days`. They are what powers the Energy dashboard and statistics
  graphs for years. This is why a household rarely needs months of raw state history.

### Risks of an external DB in another VM / the cluster

- **Startup ordering.** After a power cut, Proxmox boots both VMs. The Talos VM plus CNPG takes longer than
  HAOS. HA retries 10 x 3 s = 30 s by default, then the recorder fails to set up and history/graphs stay broken until HA
  restarts. Can be mitigated with higher retries and Proxmox startup order, but it is a new failure mode.
- **Coupling.** A cluster upgrade, a Talos reboot, a CNPG failover or a broken ArgoCD sync now affects the house.
  Automations keep running, but the recorder queues in memory and can drop data. The design goal of the separate
  HA VM was to decouple HA from the cluster.
- **Backups split.** HAOS backups include the SQLite DB. With an external DB, the HA backup no longer contains history;
  you need CNPG backups and must restore both consistently.
- **Credentials.** ESO can't write into HAOS; the DB URL lives in HA's `secrets.yaml` (manual, outside Bitwarden SM
  sync).
- **Network.** Recorder writes every few seconds over the LAN; fine bandwidth-wise, but adds latency to history queries
  vs local disk.

### Does Postgres buy anything for this household?

Little. Reasons people choose an external DB: SD-card wear on a Pi (not relevant on NVMe and ZFS), very large
installs with months of raw history, or wanting SQL/Grafana access to history. For a household with tens to low hundreds
of entities, SQLite on NVMe is fast, and HA's maintainers have spent the last years optimizing for it (see the warning
above). The main gain of Postgres here would be "one DB platform for everything", which is an aesthetic, not a
functional, win.

What to do instead:

```yaml
# configuration.yaml
recorder:
  purge_keep_days: 30        # a month of raw history; long-term stats are kept regardless
  commit_interval: 5
  exclude:
    domains:
      - update
      - automation           # optional; logbook still shows triggers while in memory
    entity_globs:
      - sensor.*_linkquality
      - sensor.*_rssi
      - sensor.*_uptime
    entities:
      - sun.sun
      - sensor.date
      - sensor.time
```

### Alternative for long-term raw history: a secondary time-series sink

- InfluxDB integration (official) streams states to InfluxDB 1.x/2.x; HA keeps working if it is unreachable (it
  buffers and drops). [HA InfluxDB integration](https://www.home-assistant.io/integrations/influxdb/)
- VictoriaMetrics accepts the InfluxDB line protocol, so the same integration can write to it, with lower resource
  use. [VictoriaMetrics docs](https://docs.victoriametrics.com/)
- Prometheus integration exposes `/api/prometheus` for scraping by the cluster's monitoring stack. [HA Prometheus
  integration](https://www.home-assistant.io/integrations/prometheus/)
- TimescaleDB (Postgres extension) is used via community projects (for example LTSS custom component) and is the
  most complex of these.

This pattern can live in the cluster safely, because it is a one-way, best-effort copy. Grafana in the cluster can then
chart years of data. Recommended only if Robert wants that.

## 3. If Postgres anyway: where

| Option | Pros | Cons |
| --- | --- | --- |
| (a) CNPG in Talos, exposed via LoadBalancer/NodePort on the LAN | Declarative, barman-cloud backups to R2 with PITR, one DB platform | HA depends on the cluster; needs LB (MetalLB/Cilium L2) or NodePort on the Talos VM IP; restart ordering; credentials hand-copied into HAOS |
| (b) Separate Postgres VM | Independent of cluster, simple | Another OS to patch, own backup story (pgBackRest/restic), more Tofu/Ansible |
| (c) Postgres/TimescaleDB app inside HAOS | Same life cycle as HA, included in HA backups | Community app (no official Postgres app; the official DB app is MariaDB); backup of a live DB via HA snapshots is less robust than SQLite's handling; no real gain over SQLite |

If (a) is chosen anyway:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: pg-homeassistant
  namespace: databases
spec:
  instances: 1
  storage:
    size: 20Gi
    storageClass: local-path
  bootstrap:
    initdb:
      database: homeassistant
      owner: homeassistant
      encoding: UTF8           # HA docs: create the DB with utf8
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: r2-homeassistant
  managed:
    services:
      disabledDefaultServices: ["ro", "r"]
      additional:
        - selectorType: rw
          serviceTemplate:
            metadata:
              name: pg-homeassistant-lan
            spec:
              type: LoadBalancer        # or NodePort if no LB implementation on Talos
              loadBalancerSourceRanges:
                - <ha-vm-ip>/32       # HA VM only
```

- Service exposure: [CNPG service management](https://cloudnative-pg.io/documentation/current/service_management/)
  ("legacy applications ... that need to reside in a virtual machine" is a listed use case).
- Backups: use the Barman Cloud Plugin (`ObjectStore` CR pointing at R2). The in-tree
  `spec.backup.barmanObjectStore` is deprecated since 1.26 and is removed in CNPG 1.31.0. Sources: [Barman Cloud
  Plugin migration guide](https://cloudnative-pg.github.io/plugin-barman-cloud/docs/migration/) and [CNPG 1.30.0 release
  notes](https://github.com/cloudnative-pg/cloudnative-pg/releases/tag/v1.30.0)
- Credentials: CNPG generates `pg-homeassistant-app` secret. You would copy the URI once into HA:

```yaml
# /config/secrets.yaml (HAOS, not in git)
recorder_db_url: postgresql://homeassistant:REDACTED@<cnpg-lan-ip>:5432/homeassistant?sslmode=require

# configuration.yaml
recorder:
  db_url: !secret recorder_db_url
  db_max_retries: 60
  db_retry_wait: 10
```

- TLS: CNPG serves TLS with its own CA. `sslmode=require` encrypts; `verify-full` needs the CA copied into HAOS `/ssl`
  and `sslrootcert=` in the URL.
- Rotation is manual (ESO cannot reach into HAOS).

## 4. HA backups with HAOS

Source: [HA backups docs](https://www.home-assistant.io/common-tasks/general/#backups)

- Native backup system (since 2025.1): scheduled, retention count, "backup before update", partial or full (config,
  apps, share, ssl, media). Backups are encrypted; the key is in the backup emergency kit, which must be stored
  safely (put it in the Neustrom or Nyström Bitwarden org).
- Locations: local, network storage (SMB/NFS), Home Assistant Cloud (one backup up to 5 GB), and integration-provided
  targets including Cloudflare R2 (official since 2026.2; note the AWS S3 integration is not R2-compatible),
  Backblaze B2, Google Drive, OneDrive and others. Sources: [HA Cloudflare R2
  integration](https://www.home-assistant.io/integrations/cloudflare_r2) and
  [home-assistant/core#152825](https://github.com/home-assistant/core/pull/152825)
- R2 setup: separate bucket (for example `neustrom-ha-backups`), a bucket-scoped "Object Read & Write" API token,
  endpoint `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Outbound only, no exposure needed.
- Known issue seen early 2026 with multipart upload errors on R2
  ([home-assistant.io#43416](https://github.com/home-assistant/home-assistant.io/issues/43416)); test a full backup and
  restore once.

Fit with the lab's backup design:

- Layer 1: HA native encrypted backups daily to R2 (offsite) and optionally to an SMB share on the backup target. Keep 7
  to 14.
- Layer 2: Proxmox `vzdump` (or PBS) of the whole HAOS VM nightly to the backup target. Fastest full restore, includes
  the disk as-is.
- Restore test: build a throwaway HAOS VM via Tofu, restore during onboarding with the emergency kit. Note: after
  restore on a new machine with a different Zigbee radio, Zigbee must be migrated.

## 5. Exposure through the cluster

### Traffic path

`Internet -> Cloudflare edge -> cloudflared (in Talos) -> Traefik -> Service ha -> EndpointSlice -> HA VM:80 (or 8123)`

An `ExternalName` Service only takes a DNS name; for a bare IP use a selectorless Service plus EndpointSlice:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: home-assistant
  namespace: home-assistant
spec:
  ports:
    - name: http
      port: 8123
      targetPort: 80          # HAOS 2026.8+ default; 8123 on older installs
---
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: home-assistant-1
  namespace: home-assistant
  labels:
    kubernetes.io/service-name: home-assistant
addressType: IPv4
ports:
  - name: http
    port: 80
endpoints:
  - addresses: ["<ha-vm-ip>"]
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: home-assistant
  namespace: home-assistant
spec:
  entryPoints: [websecure]
  routes:
    - match: Host(`ha.neustrom.net`)
      kind: Rule
      services:
        - name: home-assistant
          port: 8123
```

- WebSockets: Traefik proxies them natively, and Cloudflare Tunnel supports WebSockets. No special config needed. Don't
  let anything cache `/api/`, `/auth/`, HTML or service worker files (HA docs, "Caching behind a reverse proxy or CDN").
- Traefik `--providers.kubernetescrd.allowExternalNameServices` is only needed if you use ExternalName instead.

### HA HTTP settings (now UI, since 2026.8)

From [HA HTTP integration](https://www.home-assistant.io/integrations/http/): the `http:` YAML block was moved to
Settings > System > Network > HTTP server, and existing YAML is imported once with a repair issue asking you to remove
it. Set:

- **Trust X-Forwarded-For.** On.
- **Trusted proxies.** The Talos VM IP (Traefik pods SNAT to the node IP when reaching an off-cluster endpoint), for
  example `<talos-vm-ip>`, or the LAN network address `10.0.0.0/24` (must be a network address, not a host with mask).
  Requests from a proxy are blocked if these are not set.
- Enable IP banning with a modest attempt count.
- Ensure Traefik forwards the real client IP: trust Cloudflare's `CF-Connecting-IP`/X-Forwarded-For at Traefik
  (`forwardedHeaders.trustedIPs` for the cloudflared pod path) so HA bans the attacker, not cloudflared.

Older YAML equivalent, for reference only (pre-2026.8):

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - <talos-vm-ip>
  ip_ban_enabled: true
  login_attempts_threshold: 5
```

### Auth

- `hass-oidc-auth` v1.2.1 (2026-08-19), HACS, UI or YAML config, Authentik guide in the repo:
  [hass-oidc-auth](https://github.com/christiaangoossens/hass-oidc-auth) (provider guide:
  `docs/provider-configurations/authentik.md`; also [Authentik Home Assistant
  guide](https://integrations.goauthentik.io/miscellaneous/home-assistant/)). Callback
  `https://ha.neustrom.net/auth/oidc/callback`, public client with PKCE recommended.
- Mobile app: login uses a device code shown in the app, confirmed in a browser. Per the FAQ this is deliberate
  until the HA apps support custom tabs / ASWebAuthenticationSession.
- The FAQ says to remove any reverse-proxy auth layer once the integration is in place, and to configure
  trusted proxies so the real client IP reaches HA.
- So there is no Cloudflare Access and no Authentik forward-auth on the HA route. This is an exception to the draft ADR
  0001 rule "CI fails any public route without Authentik"; the ADR/CI rule should allow "app-native OIDC with Authentik"
  as an alternative to forward-auth. ADR 0001 now includes that alternative.
- Hardening instead: keep a local HA admin with MFA (TOTP) as break-glass; Cloudflare WAF rate limit on `/auth/*`;
  optional Cloudflare geo rule. Long-lived tokens for any integrations.
- Mobile app URLs: external `https://ha.neustrom.net`, internal `http://<ha-vm-ip>` on the home Wi-Fi SSID.

## Open questions only Robert can answer

1. Zigbee: which coordinator (USB stick or network coordinator), and ZHA or Zigbee2MQTT? Existing Zigbee network to
   migrate?
2. Matter/Thread: any Thread devices planned? Then a Thread radio and IPv6 on the LAN matter.
3. Bluetooth: devices that need it (presence, plant sensors)? USB dongle or ESPHome proxies?
4. History: how much raw history do you want (default 10 days; suggest 30)? Do you want Grafana charts over years (then
   add InfluxDB/VictoriaMetrics as a secondary sink)?
5. Is there an existing HA install to migrate (backup restore) or a fresh start?
6. Do you want HA's `/config` in git (read-only mirror for portfolio/audit), knowing most state is in `.storage/`?
7. Do you want Nabu Casa (Home Assistant Cloud) at all, for example as a second backup location or Alexa/Google voice,
   or strictly Cloudflare Tunnel?
8. Where should the backup emergency kit live: Neustrom (lab) or Nyström (household passwords) Bitwarden org?
