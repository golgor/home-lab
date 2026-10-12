---
status: accepted
date: 2026-10-11
---

# local-path volumes on the ZFS mirror instead of Longhorn

The Talos cluster needs a storage driver for persistent volumes. We decided to use `local-path-provisioner` on a
dedicated VM disk that sits on the host's ZFS mirror. Longhorn's main feature, copying each volume across nodes, does
nothing on a single node, and the ZFS mirror already covers a failed disk.

## Considered options

- Longhorn. It gives replicated block storage, snapshots, S3 backups and a UI. It needs about three nodes to make
  sense, uses noticeable CPU and RAM, adds a layer that can fail, and needs extra system extensions on Talos.
- OpenEBS or another distributed driver. Same trade-off as Longhorn for a single node.

## Consequences

- A volume lives only on the one node, so off-box backups of volumes are required, through Velero or restic. The tool
  is still open.
- Moving to more nodes later means migrating volumes to a distributed driver. Revisit this decision at three nodes.
