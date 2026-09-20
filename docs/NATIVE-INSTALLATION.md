# OrdaX Native Installation

Status: POST-MVP FOUNDATION — PRESERVED / MVP CAPABILITY DISABLED

Machine-readable authority: `docs/contracts/native-installation.json`.

The public MVP is **USB-only**. It boots and runs OrdaX directly from authorized removable media and does not offer installation to SSD/NVMe/HDD.

This document preserves the Native installation foundation for a **post-MVP** phase. Native installation is not a different OrdaX product; when activated later it will install the same verified release using the `native-disk` storage profile from `docs/contracts/storage-architecture.json`.

For Stable/MVP, the Native capability, target-discovery token and internal-disk destructive operations remain disabled/inaccessible even if their source code and CI proofs exist.

Execution mode is explicit rather than inferred from hardware:

```text
/ordax/bootstrap/config/product-mode
  usb          -> live/portable OrdaX; installer capability may be available
  native-disk  -> installed OrdaX; Native installer capability is forbidden
```

The Stable bootstrap passes this identity as `ORDAX_PRODUCT_MODE` through guardian, supervisor and Surface. The future physical installer must write `native-disk` into the target bootstrap before first boot. The shared signed `system.tar` is the same in both modes; this marker does not fork the product.

## Future post-MVP activation scope

If Native installation is promoted after the MVP, the first activation should remain deliberately smaller than a general-purpose partition editor:

- whole-disk installation only;
- explicit target-disk selection;
- explicit warning that existing target data will be erased;
- the booted OrdaX USB can never be selected as the target;
- no automatic shrinking of Windows/Linux partitions;
- no "install alongside" flow in the first MVP;
- no manual partition editor in the first MVP.

This keeps the first destructive path auditable and avoids pretending that dual-boot migration is safe before it has its own contracts and hardware proof.

## Native target

```text
GPT
├─ ORDAX-ESP   FAT32
└─ ORDAX-POOL  LUKS2 -> Btrfs
```

The pool fills the remaining usable target capacity. System deployments, apps, persistent machine state and user data share that pool through logical boundaries instead of rigid fixed-size partitions.

## Target identity boundary

The Native installer must not treat a device path such as `/dev/sda` as sufficient identity. The adapter must provide a stable device identity plus the current device path, exact capacity, logical-sector size and read-only/source-boot flags. The Creator Core binds those fields into a SHA-256 confirmation fingerprint.

The current Core implementation is:

```text
read-only adapter enumeration
 -> FinalizeNativeInstallTarget
 -> user selects exact target
 -> confirmation fingerprint
 -> re-enumerate
 -> MatchConfirmedNativeInstallTarget
 -> PlanNativeInstallationForTarget
 -> still no APPLY permission
```

Changing capacity, device path, serial/stable identity, read-only state or source-boot classification invalidates the confirmation. The currently booted OrdaX USB is always ineligible as a Native installation target.

The fixed initramfs is deliberately **not** expanded for the installer. Once OrdaX is running, `/ordax` is already the mounted bootstrap/release filesystem. The Linux Creator adapter resolves the exact backing block device from `/proc/self/mountinfo`, maps that partition to its containing physical disk and marks that disk as the source boot medium.

`ordax-creator-native-targets` refuses all target selection when the `/ordax` mount is absent, ambiguous or not backed by a canonical `/dev/...` source. No manual source-device input is part of the normal MVP path; the explicit source-file flag exists only for bounded tests/recovery engineering.

Transport alone is not authority: an internal NVMe/SATA disk and a suitable external SSD may both use the Native profile, while the source live USB remains forbidden.

## Future activation phases

```text
inspect target
 -> produce non-destructive plan
 -> bind confirmation to exact target identity
 -> create GPT
 -> create ORDAX-ESP
 -> create encrypted ORDAX-POOL
 -> create Btrfs/subvolume layout
 -> materialize verified Stable release
 -> install signed boot + recovery assets
 -> read-back / structural verification
 -> reboot without USB
 -> first-boot health
 -> promote known-good
```

No installation is complete merely because files were copied. Promotion requires a bootable verified deployment and first-boot health.


### Native initramfs runtime proof

The dedicated Native initramfs is now built from an exact CI-observed and byte-locked userspace closure. A disposable runtime proof executes the **packaged** BusyBox, `cryptsetup` and `btrfs` bytes against a regular-file-backed LUKS2 container, creates the canonical subvolumes, writes/reads back `product-mode=native-disk`, reopens the mapper read-only and proves that a read-only Btrfs mount rejects writes. The ephemeral key and container are destroyed before success.

This closes the packaged LUKS2/Btrfs userspace gate only. It does **not** prove UEFI boot, kernel command-line parsing, PID 1 handoff, first-boot health or physical installation.

The shared kernel configuration has also been compiled and its resolved `.config` proves device-mapper/dm-crypt, AES-XTS and Btrfs are built in. A new exact-head provenance run is required before that kernel candidate is consumed as a Native ESP boot artifact.

## Current implementation boundary

The Creator Core already implements target geometry in:

`tools/creator/core/storage_profiles.go#PlanNativeDiskTargetStorage`

The first MVP implementation slice adds a pure, non-destructive Native installation plan:

`tools/creator/core/native_install.go#PlanNativeInstallation`

and exposes it through:

`ordax-creator plan-native --target-bytes <bytes>`

This command touches no physical device and authorizes no write.

The storage materialization path is now proven in disposable CI: exact GPT geometry, FAT32 ESP, LUKS2 ORDAX-POOL, Btrfs, canonical subvolumes, product-mode materialization and readback all pass without opening a physical target. The proof destroys its ephemeral RAW/container bytes and key and publishes metadata only.

That storage proof is deliberately **not a boot claim**. Physical APPLY, verified Stable release materialization into the target, verified Native boot/recovery assets, unlock/boot proof and first-boot promotion remain separate fail-closed gates.

## Stable/MVP rules

The Native installer:

- does not use operational Git;
- consumes only an authorized signed Stable release;
- verifies artifact size/hash/signature through the release trust path;
- preserves known-good/recovery semantics;
- must fail closed when target identity, release trust or installation verification is ambiguous.

Owner/Development may continue to have different engineering/recovery tooling, but it must not become the public Native installation contract.
