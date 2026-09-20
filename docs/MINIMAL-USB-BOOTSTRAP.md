# Minimal USB Bootstrap

Status: CANONICAL FOR PROTOTYPE

## Goal

The bootstrap seed contains only the minimum trusted substrate required to boot and reach the selected acquisition mechanism. It is not a preinstalled copy of the complete OrdaX product.

There are two supported acquisition profiles:

- owner/development Git-first: network -> Git -> partial+sparse checkout of `main` -> `system/entrypoint`;
- canonical signed release: network -> signed release acquisition -> verification -> immutable activation.

The profiles share the same source authority (`main`) and the same principle: ordinary `system/` changes must not require reflashing the USB.

## Physical layout model

Three contracts coexist during migration and must not be confused.

### Capacity-independent bootstrap seed — transitional source artifact

```text
ORDAX-ESP
ORDAX
```

Exactly two seed partitions.

The seed is capacity-independent and remains the source object described by `docs/contracts/physical-media.json`. It is retained while the existing boot chain is proven; it is **not** the durable MVP product layout.

### Current physical owner/development proof — transitional

```text
ORDAX-ESP
ORDAX
ORDAX-DATA
```

Exactly three prepared-target partitions.

This is governed by `docs/contracts/physical-prepared-media.json` and remains useful for current real-hardware validation. It must not be promoted as the long-term Stable/MVP storage architecture.

### Durable Stable/MVP USB target — v2

The durable product bootstrap is governed separately by `docs/contracts/portable-bootstrap-v2.json`. Unlike the transitional network-first seed, the **MVP product USB is offline-capable on first boot**: the Creator must already place one signed/verified `system.erofs` release on `ORDAX-DATA` and initialize the ext4 state image so `current` and `known-good` point to that exact release.

This does not preinstall the full product on the ESP. `ORDAX-ESP` remains boot/bootstrap-only. The product release stays under `ORDAX-DATA/.ordax/releases/`.


```text
ORDAX-ESP   FAT32
ORDAX-DATA  exFAT
```

Exactly two physical product partitions. There is no fixed physical `ORDAX` system partition.

```text
ORDAX-DATA/
├─ user files...
└─ .ordax/
   ├─ releases/<version>.erofs
   └─ state/persistent-state.img   # ext4 inside
```

The Creator Core geometry is `PlanPortableTargetStorage`. The storage contract is `docs/contracts/portable-usb-v2.json`, backed by `docs/contracts/storage-architecture.json`.

The v2 storage proof is intentionally non-destructive. The physical writer must remain on the transitional profile until v2 storage, kernel prerequisites, boot/initramfs handoff, recovery and physical-write planning have passed their independent gates.

## Bootstrap seed payload

### ORDAX-ESP

Only boot-critical material:

```text
UEFI bootloader
loader configuration
verified kernel
verified initramfs
recovery entry when required
```

### ORDAX main partition

Common roots are limited to bootstrap/runtime state. The exact payload depends on the acquisition profile.

Owner/development Git-first base:

```text
/ordax/dev-base/            # minimal runtime substrate
  shell/libc/libs
  selected drivers/modules
  selected firmware
  network tools
  CA certificates
  Git
  apk client + Alpine trust keys   # signed runtime acquisition only

/workspace/ordax/           # created at runtime, persistent, not preseeded
/state/ordax/               # Git state + replaceable runtimes after switch_root
```

The apk client is not permission to turn the base into a normal package-managed desktop. Pulled `system/` code may use it to materialize versioned, replaceable runtime roots under `/state`; Cage/Cog/Mesa and other high-level product/runtime packages remain outside the fixed seed.

Canonical signed-release base:

```text
/ordax/bootstrap/
  network/
  release-acquisition/
  recovery/

/ordax/releases/            # initially empty
/ordax/current              # unset until first release is verified
/ordax/state/               # empty/minimal runtime root
/ordax/home/                # user-data root
```

## Explicitly absent from the seed

```text
normal full Surface/runtime preinstall = NO
normal apps preinstall = NO
high-level services = NO
stable device identity service = NO
Remote Core = NO
Control Plane = NO
SSH = NO
complete repository checkout = NO
build toolchain = NO
WSL/QEMU payload = NO
legacy repository dump = NO
```

A tiny local status/recovery presentation is allowed only if required to show network, acquisition, verification or failure state.

## Owner/development Git-first boot

```text
UEFI
 -> kernel/initramfs
 -> mount LABEL=ORDAX
 -> switch_root to development base
 -> selected drivers/firmware
 -> network
 -> Git
 -> partial+sparse clone of main when checkout is absent
 -> otherwise git pull --ff-only
 -> /workspace/ordax/system/entrypoint
 -> pulled system may materialize a replaceable runtime under /state
 -> OrdaX
```

Current checkout policy:

```text
REMOTE=origin expected repository only
BRANCH=main expected branch only
LOCAL_MODIFICATIONS=BLOCK_PULL
CLONE_FILTER=blob:none
SPARSE_CHECKOUT=/system/ + /bootstrap/base-update/ + selected update/trust contracts
PERSISTENT_CHECKOUT=YES
ROLLBACK_PIN_SURVIVES_REBOOT=YES
EXPLICIT_ORDAX_PULL_RELEASES_PIN=YES
```

A valid local checkout may boot when the network is unavailable. A rollback is sticky across reboot and must not be silently advanced by boot-time synchronization. A runtime already materialized under `/state` is reusable offline; network is needed only for its first acquisition or a version change that requires new package bytes.

## Canonical signed-release first boot

### Current transitional path

This remains network-first and exists for the current hardware proof. It is not the final Stable/MVP first-boot UX.

```text
UEFI
 -> kernel/initramfs
 -> mount ORDAX ext4
 -> minimal bootstrap
 -> network when no known-good release exists
 -> acquire release envelope/artifacts over HTTPS
 -> verify integrity/authenticity
 -> materialize /ordax/releases/<commit>
 -> atomically activate /ordax/current
 -> launch OrdaX
```

### Durable portable-v2 target

The final MVP path removes the physical `ORDAX` partition. The future v2 initramfs handoff must instead:

```text
UEFI
 -> kernel/initramfs with exFAT + EROFS + loop + ext4 + OverlayFS built in
 -> mount ORDAX-DATA
 -> resolve verified current/known-good release image
 -> attach immutable EROFS release
 -> attach Linux-native ext4 persistent-state image
 -> compose writable runtime without using exFAT as OverlayFS upper
 -> launch verified OrdaX release
```

Activation metadata for the durable USB is intentionally **not** stored as a symlink or mutable pointer directly on exFAT. The fixed ext4 persistent-state image owns `current`, `known-good`, `candidate` and the activation transaction. This keeps Linux activation/rollback state on a Linux-native filesystem with atomic replacement and fsync semantics, while exFAT remains a byte store for immutable releases and user-visible files.

The repository now also has a disposable **mount-handoff proof** for this graph. It re-verifies a signed portable release offline, mounts the real EROFS system tree read-only, mounts the ext4 persistent-state image, composes an OverlayFS runtime system view and proves persistent writes do not mutate EROFS.

That still does **not** mean the v2 boot handoff is implemented. The current fixed initramfs does not yet contain the required `losetup` capability or portable handoff helper, and release selection/known-good fallback metadata has not yet been connected. Until those boot/recovery gates are green, the current transitional boot path remains the hardware validation path.

Remote access is not needed for either Stable/MVP path.

## After acquisition

Owner/development:

```text
NETWORK_REQUIRED_FOR_VALID_LOCAL_CHECKOUT_BOOT=NO
LOCAL_CHECKOUT_PRESERVED=YES
ROLLBACK_LOCAL=YES
NORMAL_SYSTEM_CHANGE_REQUIRES_REFLASH=NO
```

Canonical release:

```text
NETWORK_REQUIRED_FOR_KNOWN_GOOD_BOOT=NO
KNOWN_GOOD_RELEASE_PRESERVED=YES
ROLLBACK_LOCAL=YES
NORMAL_SYSTEM_CHANGE_REQUIRES_REFLASH=NO
```

Network/Git are required to acquire new development source or new release bytes, not to boot an already valid local state.

## Development model

Owner/development USB:

```text
system/Surface/app/native-host change
 -> Git push main
 -> ordax-pull
 -> ordax-run
 -> pulled code may provision/update replaceable runtime state
 -> no USB reflash

boot/kernel/initramfs/dev-base hardware support change
 -> separately built base candidate
 -> repository-delivered base-update control stages inactive slot
 -> next boot activates candidate
 -> manual USB reflash only when the bootstrap itself cannot recover/update
```

Canonical release:

```text
system/Surface/app change
 -> Git push
 -> CI builds signed release/delta
 -> updater acquires
 -> verify + activate
 -> no USB reflash
```

## Source/media relationship

Everything needed to reproduce the bootstrap is represented in this repository through source, manifests, configuration, provenance and build recipes. The running development checkout intentionally materializes only the product runtime plus the small base-update control plane; large boot artifacts are built from repository source and delivered as base candidates rather than compiled on the notebook.

Private/runtime data is not committed to public Git. The USB is never source authority.

## Trust boundary

The owner/development Creator may use explicitly marked ephemeral prototype trust for development provenance. This does not satisfy canonical release trust and must never be promoted as such.

Canonical public release acquisition remains blocked until the user-controlled release signing ceremony/public anchor is completed.

## Prototype rules

```text
GIT_MAIN_IS_SOURCE_AUTHORITY=YES
BOOTSTRAP_SEED_PARTITIONS=2
TRANSITIONAL_PREPARED_USB_PARTITIONS=3
MVP_TARGET_PREPARED_USB_PARTITIONS=2
MVP_TARGET_PORTABLE_LAYOUT=ORDAX-ESP+ORDAX-DATA
MVP_TARGET_BOOT_HANDOFF_IMPLEMENTED=NO
SEPARATE_HOME_PARTITION=NO
REMOTE_CONTROL_PRESEEDED=NO
SSH_PRESEEDED=NO
FULL_SYSTEM_PRESEEDED=NO
COMPLETE_SOURCE_CHECKOUT_PRESEEDED=NO
BUILD_TOOLCHAIN_PRESEEDED=NO
REFLASH_FOR_NORMAL_SYSTEM_CHANGES=NO
```

If a future requirement proves that device identity, Remote Core or Control Plane is necessary, it must be introduced deliberately through an architectural decision rather than added preemptively.


### Portable v2 bootstrap capsule candidate

The durable USB now has a deterministic bootstrap-capsule candidate at `/ordax/bootstrap/bootstrap.erofs`.

The capsule is deliberately small: the static release agent, local recovery entrypoint and official release-channel pointer. It excludes Surface, normal apps, user data, Git, build tools and every private signing key. The canonical public release trust anchor remains a separate bootstrap-owned object.

CI builds the EROFS capsule twice from normalized tar metadata and requires byte-identical output plus EROFS integrity verification. This proves the candidate format only. The capsule is **not yet materialized into the physical ESP**, its hash is not yet pinned inside the fixed initramfs, and PID1 does not mount or execute it. Those remain independent promotion gates.


### Portable-v2 candidate PID1

The fixed initramfs now carries an isolated candidate orchestrator at `/sbin/ordax-portable-init`. It is **not** the default `/init`, and no physical systemd-boot entry points to it.

The candidate path is intended only for disposable boot proof through `rdinit=/sbin/ordax-portable-init`. It mounts the ESP read-only, verifies the bootstrap capsule against the initramfs-owned hash, mounts `ORDAX-DATA`, verifies the pinned Stable Base, attaches the ext4 state image, and then evaluates boot slots in this order:

```text
current
 -> exact signed offline verification
 -> if invalid: known-good
 -> exact signed offline verification
 -> candidate is never boot authority
```

Only after a release passes exact signature/hash verification does the candidate compose the Stable Base overlay, bind the verified `system/` subtree read-only, move all required mounts under the new root and invoke `switch_root` into `ordax-stable-init`.

This does not claim a bootable MVP yet. Canonical public trust is still not pinned, the candidate has no physical boot entry, QEMU end-to-end proof is still pending, and the transitional `/init` remains the actual physical boot path.
