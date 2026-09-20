# OrdaX Native Installation

Status: MVP REQUIRED — PLAN IMPLEMENTED, APPLY PENDING

Machine-readable authority: `docs/contracts/native-installation.json`.

The MVP must support two distinct outcomes after booting an authorized Stable/MVP USB:

```text
OrdaX USB
  -> Use OrdaX directly from USB
  -> Install OrdaX to SSD / NVMe / HDD
```

Native installation is not a different OrdaX product. It installs the same verified Stable release using the `native-disk` storage profile from `docs/contracts/storage-architecture.json`.

Execution mode is explicit rather than inferred from hardware:

```text
/ordax/bootstrap/config/product-mode
  usb          -> live/portable OrdaX; installer capability may be available
  native-disk  -> installed OrdaX; Native installer capability is forbidden
```

The Stable bootstrap passes this identity as `ORDAX_PRODUCT_MODE` through guardian, supervisor and Surface. The future physical installer must write `native-disk` into the target bootstrap before first boot. The shared signed `system.tar` is the same in both modes; this marker does not fork the product.

## Initial MVP scope

The first public installer is deliberately smaller than a general-purpose partition editor:

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

## Required installation phases

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

## Current implementation boundary

The Creator Core already implements target geometry in:

`tools/creator/core/storage_profiles.go#PlanNativeDiskTargetStorage`

The first MVP implementation slice adds a pure, non-destructive Native installation plan:

`tools/creator/core/native_install.go#PlanNativeInstallation`

and exposes it through:

`ordax-creator plan-native --target-bytes <bytes>`

This command touches no physical device and authorizes no write. Physical APPLY, encryption provisioning, filesystem creation, release materialization and first-boot promotion remain separate gates.

## Stable/MVP rules

The Native installer:

- does not use operational Git;
- consumes only an authorized signed Stable release;
- verifies artifact size/hash/signature through the release trust path;
- preserves known-good/recovery semantics;
- must fail closed when target identity, release trust or installation verification is ambiguous.

Owner/Development may continue to have different engineering/recovery tooling, but it must not become the public Native installation contract.
