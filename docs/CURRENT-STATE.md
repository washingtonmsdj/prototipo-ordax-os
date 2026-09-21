# Current State

Status date: 2026-09-20

This is the canonical handoff snapshot. Architecture/contracts win if another document conflicts with it. Detailed historical evidence remains under `docs/evidence/`; this file records the current boundary without treating CI proof, development-hardware proof and product-release authorization as interchangeable. Values that mirror structured source — including product/app versions, component release modes and physical-media geometry — are regression-checked against their owners so this snapshot cannot silently drift from the implementation.

## MVP scope decision — USB only

```text
MVP_PUBLIC_EXECUTION_MODE=USB_ONLY
MVP_NATIVE_INSTALLATION_AVAILABLE=NO
MVP_INTERNAL_DISK_DESTRUCTIVE_WRITE=NO
NATIVE_FOUNDATION_RETAINED_FOR_POST_MVP=YES
MVP_BILLING_IMPLEMENTED=NO
MVP_PRICING_DEFINED=NO
MVP_COMMERCIAL_DEVICE_LIMIT_DEFINED=NO
WEB_MOBILE_SYNC_PUBLIC_STATUS=COMING_SOON_ONLY
```

Native contracts, Creator Core, LUKS2/Btrfs work, Native initramfs, ESP and disposable proofs remain valid engineering foundation, but they do not block or appear as user-facing MVP functionality.

## Repository

```text
REPOSITORY=washingtonmsdj/prototipo-ordax-os
ROLE=CLEAN_ROOM_PROTOTYPE
DEFAULT_BRANCH=main
PROMOTED_TO_OFFICIAL=NO
LEGACY_REPOSITORY=washingtonmsdj/novo-ordax-os
LEGACY_REPOSITORY_IS_REFERENCE_ONLY=YES
GIT_MAIN_IS_SOURCE_AUTHORITY=YES
USB_IS_SOURCE_AUTHORITY=NO
```

## Product model

```text
ONE_PRODUCT=YES
MODES=WEB,MOBILE,DESKTOP,USB,NATIVE_DISK
ONE_ACCOUNT_MODEL=YES
ONE_SURFACE_SOURCE=YES
CAPABILITY_DIFFERENCES_VIA_ADAPTERS=YES
SYSTEM_ENTRYPOINT_IMPLEMENTED=YES
SURFACE_BOOTSTRAP_RUNTIME=YES
GRAPHICAL_SURFACE_SOURCE=IMPLEMENTED
SHARED_WORKSPACE_WINDOW_MODEL=IMPLEMENTED
FIRST_PARTY_APP_REGISTRY=FILES,NOTES,INTERNET,SETTINGS,ACCOUNT,SYSTEM
SETTINGS_VISIBLE_LABEL=AJUSTES
SURFACE_HOME_TECHNICAL_UPDATE_MARKERS=REMOVED
PRODUCT_VERSION=0.1.0
PRODUCT_VERSION_LABEL=v0.1.0
PRODUCT_MATURITY=PROTOTYPE
PRODUCT_V1_RESERVED_FOR_STABLE_RELEASE=YES
FIRST_PARTY_APP_VERSIONING=PER_COMPONENT
FIRST_PARTY_APP_PRE_1_0_MATURITY=BETA
APP_FILES_VERSION=0.1.0
APP_FILES_MATURITY=BETA
APP_FILES_RELEASE_MODE=bundled
APP_SETTINGS_VERSION=0.1.0
APP_SETTINGS_MATURITY=BETA
APP_SETTINGS_RELEASE_MODE=bundled
APP_ACCOUNT_VERSION=0.1.0
APP_ACCOUNT_MATURITY=BETA
APP_ACCOUNT_RELEASE_MODE=bundled
APP_SYSTEM_VERSION=0.1.0
APP_SYSTEM_MATURITY=BETA
APP_SYSTEM_RELEASE_MODE=bundled
APP_INTERNET_VERSION=0.3.0
APP_INTERNET_MATURITY=BETA
APP_INTERNET_RELEASE_MODE=git-app
APP_NOTES_VERSION=0.4.0
APP_NOTES_MATURITY=BETA
APP_NOTES_RELEASE_MODE=git-app
PRODUCTION_INDEPENDENT_APP_UPDATES_ENABLED=NO
SYSTEM_UPDATE_SCOPE=BASE,SURFACE,SERVICES,SYSTEM
APPLICATION_UPDATE_SCOPE=FILES,NOTES,INTERNET,SETTINGS,ACCOUNT
UPDATE_HUMAN_IDENTITY=DELIVERY_NUMBER
UPDATE_PR_NUMBER_IS_PRODUCT_IDENTITY=NO
UPDATE_RUNNING_LABEL=EM_EXECUCAO
WEB_CLIENT_CANDIDATE=PASS
APPEARANCE_THEME_VALUES=DARK,LIGHT
SURFACE_ACCESSIBILITY_PREFERENCES=CONTRAST,MOTION,TEXT_SCALE
SURFACE_TEXT_SCALE_VALUES=STANDARD,LARGE,EXTRA_LARGE
APPEARANCE_PERSISTENCE=WEB_LOCAL_PASS
APPEARANCE_ACCOUNT_SYNC=NO
NATIVE_GRAPHICAL_HOST=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_PRIMARY_INPUT=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_POWER_RESTART=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_POWER_SHUTDOWN=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_GIT_HOT_UPDATE=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_UPDATE_SELF_HEALING=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_GUARDIAN_SUPERVISOR=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_RESCUE_CHANNEL=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_TELEMETRY_RELAY=PASS_PHYSICAL_DEVELOPMENT_USB
NATIVE_CANDIDATE_PREFLIGHT_SUCCESS_PATH=PASS_PHYSICAL_DEVELOPMENT_USB
CANONICAL_KERNEL_ACPI_BATTERY_SUPPORT=EXPLICIT
CANONICAL_KERNEL_SYSRQ_RESTART_FALLBACK=EXPLICIT
REAL_SYSTEM_BUNDLE_REPRODUCIBLE=PASS
GRAPHICAL_SURFACE_COMPLETE=NO
CANONICAL_SYSTEM_RUNTIME_COMPLETE=NO
```


The first formal human product version is **OrdaX Prototype v0.1.0**. Product version, Entrega, Git SHA and component/app versions are separate identities: v0.1.0 identifies the prototype product milestone, Entrega identifies the notebook-facing delivery sequence, the SHA remains the exact technical build identity, and each component may evolve its own SemVer. First-party apps on the `0.x` line are **Beta**; `1.0.0` remains reserved for the first stable release of each app. Internet is currently `0.3.0 Beta` and Notes is `0.4.0 Beta`, both using `git-app` in Owner/Development. Arquivos, Ajustes, Conta and Sistema are `0.1.0 Beta` and remain `bundled`. A component having its own version does not mean it already has a production-independent update channel: `git-app` is a development delivery mode, while production-independent activation remains gated behind the signed `component-slot` path with pending health, promotion and rollback. Product v1.0 remains reserved for the stable product rather than being inferred from prototype maturity, component versions or delivery count.

`system/` is the shared product source. The native development path is physically proven through `system/entrypoint (guardian) -> system/supervisor -> system/surface/entrypoint -> system/surface/bin/ordax-surface`; repository CI also proves that the actual `system/` tree can be bundled deterministically as `system.tar`.

The shared graphical source remains under `system/surface/ui/` with platform-neutral contracts, workspace/window lifecycle and capability-driven app availability. Notes is a first-party **application** with stable app id `notes`, version `0.4.0 Beta` and `git-app` delivery in Owner/Development. Native/USB may enrich it through the optional `filesystem.user-space` capability, and a future signed `component-slot`/app-package flow can target that same app identity instead of creating a Native-only fork. A general Store/package manager and production-independent app updater are not implemented yet. Notes provides local projects, a visual structured-text editor, editable checklists, real local-file/web references, autosave and device-local Native persistence through a bounded loopback state endpoint; Web uses local browser persistence with an explicit session fallback. Notes stores rich formatting as bounded blocks/marks rather than raw HTML or visible Markdown, keeps a plain-text body for search/import continuity, and migrates existing local snapshot schema v1 state to schema v2 on validation/save. Project organization now has a complete local lifecycle: projects can be renamed, non-base projects can be removed without deleting their notes, selected notes can move between projects, and checklist items can be removed. The stable `Meu espaço` project remains the non-destructive fallback for notes from removed projects. Internet is the first-party browser app with stable id `internet`, version `0.3.0 Beta` and `git-app` delivery in Owner/Development; this version identity does not claim a production Store/updater. Its shared Surface owns the approved concept structure (navigation toolbar, workspace/tab rail, central web viewport and project-context panel), while Native/USB provide `browser.web-content` through a separate unprivileged WebKit context and one external WebView per tab. The native slice supports up to 16 tabs, back/forward/reload, tab search, keyboard accelerators, persisted public tab URLs/order/active tab, project-context selection, explicit saved web references with bounded per-reference notes, automatic reference cleanup after project removal, public-network filtering and an exact loopback Host/browser-provenance boundary. Saved project references are owned by a neutral project-domain runtime and persist in the Native privileged profile with honest session fallback; the external page never receives project storage capability. Web intentionally exposes an unavailable browser-session port rather than pretending arbitrary sites can be safely embedded. Notes web references activate this same `internet` app. Internet also owns bounded device-local favorites through a neutral `ordax.browser-favorites/1` port; the Native privileged profile persists them while external website WebViews receive no access to that store. Native hardware proof for the new WebKit host remains pending, so the browser slice is implemented in source but not yet marked physically proven. Ajustes now owns persisted Surface-level contrast, motion and text-scale preferences; text scale changes the shared typographic base without claiming host-level accessibility control. Platform-specific behavior belongs in adapters/compositions, not in forks of the shared Surface. The normal Home now keeps technical delivery/recovery markers out of the area label; real delivery identity and update details live in Sistema. The visible settings identity is standardized as **Ajustes** while preserving the stable internal app id `settings`.

On the target notebook, the owner/development USB has physically proven the Git-first native host: Cage/Wayland + Barkery/WebKitGTK renders the shared Surface fullscreen; keyboard and mouse/touchpad work; authenticated native restart and shutdown work; and Git changes can be pulled and applied with a Surface reload while the notebook remains running. The temporary live-update marker appeared and then disappeared automatically in the same running session, proving the rebootless update round trip.

The Git-first update path is now split between a stable `system/entrypoint` guardian and a child `system/supervisor`. Ordinary Surface changes reload the browser, native-host changes restart only the Surface, supervisor/guardian changes use a controlled supervisor restart, and boot/bootstrap changes are marked as requiring a later reboot instead of rebooting automatically. The guardian monitors the supervisor's state-file heartbeat and can restart a stalled supervisor child without returning to the Development Base maintenance shell. The controlled `exit 75 -> guardian refresh -> supervisor restart` path has been physically exercised on the target notebook.

Recovery no longer depends on that supervisor alone. A persistent, bounded `ordax-rescue` agent lives under `/state/ordax/rescue/` and consumes only target-bound, monotonic commands from the separate Git rescue ref. The physical notebook has acknowledged multiple rescue generations, including no-op generations while healthy. The rescue protocol does not provide remote shell, arbitrary commands, reboot, poweroff or arbitrary Git reset.

Operational observability is also physically active through the temporary Supabase relay. A host-base telemetry agent starts before the graphical runtime and reports checkout SHA, human `deliveryNumber`, pending `bootRefreshRequired`, updater state, health state, rescue generation/action, power-action proof fields and a supervisor state-file heartbeat. The deployed relay configuration is source-controlled. Supabase is observation-only and has no command semantics. This allowed the recovery from the stale `d071477a` graphical session to be diagnosed and verified without relying on the visible screen.

A native-host update delivered through the live Git path has been physically validated to restart only the Surface and return to the graphical session without rebooting the notebook. Candidate Git objects are now preflighted before switching the live checkout, and the valid-candidate success path has been physically exercised; rejection/rollback of an intentionally broken candidate remains a separate physical exercise. The development Base channel also materializes an exact-commit `rootfs.tar` into a versioned root. Acquisition is delegated by the supervisor to the persistent base-update owner and runs inside the replaceable native runtime, so the minimal development Base does not gain a Python dependency. The Git-refreshable `ordax-dev-init` then selects that root only when its SHA matches the one-shot A/B candidate slot. The mapping is per slot and preserves the seed Base as the legacy fallback. The selector/materializer is source/CI work only: `dev-base-ready-sha` is not yet consumed by an ESP staging/one-shot activation owner, so this change does not arm a boot candidate. Disposable selector proof, authorized A/B staging and broken-candidate physical rollback remain separate gates; none is claimed as physical proof here. The durable offline sync-state store is implemented and CI-proven; survival of a deliberately created pending mutation across a later explicit Surface restart remains a separate physical persistence exercise.

These development-USB results do **not** imply that the canonical signed release-acquisition/native-disk product path is complete. `GRAPHICAL_SURFACE_COMPLETE` and `CANONICAL_SYSTEM_RUNTIME_COMPLETE` remain `NO` until their separate product gates close.

## Development USB — physically proven path

```text
OWNER_DEVELOPMENT_USB_BOOT=PASS
DEVELOPMENT_GIT_CHECKOUT=PASS
DEVELOPMENT_NETWORK_FOR_GIT=PASS
REPLACEABLE_NATIVE_RUNTIME=PASS
CAGE_WAYLAND_RENDER=PASS
BARKERY_WEBKIT_RENDER=PASS
PHYSICAL_KEYBOARD=PASS
PHYSICAL_MOUSE_TOUCHPAD=PASS
NATIVE_RESTART=PASS
NATIVE_SHUTDOWN=PASS
RETURN_BOOT_AFTER_SHUTDOWN=PASS
GIT_HOT_UPDATE_RELOAD=PASS
GIT_HOT_UPDATE_ROUND_TRIP=PASS
GUARDIAN_SUPERVISOR_RESTART=PASS
INDEPENDENT_GIT_RESCUE=PASS
HOST_BASE_REMOTE_TELEMETRY=PASS
CANDIDATE_PREFLIGHT_VALID_PATH=PASS
USB_REFLASH_REQUIRED_FOR_NORMAL_SYSTEM_CHANGES=NO
SSH_REQUIRED=NO
REMOTE_CONTROL_PLANE_REQUIRED=NO
```

The physical evidence is recorded in `docs/evidence/physical-native-surface-2026-09-17.md`. The original BusyBox `command -v` handoff failure was corrected in PR #21 and subsequent owner/development USB boots progressed through the Git checkout into the graphical Surface, so that historical bring-up blocker is closed for this development path.

## Build autonomy

```text
CODEX_REQUIRED=NO
LOCAL_DEVELOPER_TOOLCHAIN_REQUIRED=NO
MANUAL_KERNEL_BUILD_REQUIRED=NO
CI_BUILD_REQUIRED=YES
ARTIFACT_PROVENANCE_REQUIRED=YES
ARTIFACT_SHA256_REQUIRED=YES
PINNED_KERNEL_BUILD_ENVIRONMENT=PASS
KERNEL_REPEAT_DIGEST_PROOF=PASS
GITHUB_ACTIONS_IMMUTABLE_SHA_POLICY=PASS
GITHUB_ACTIONS_MUTABLE_TAGS=FORBIDDEN
GITHUB_ACTIONS_UNKNOWN_EXTERNAL_REFS=FORBIDDEN
GITHUB_ACTIONS_PULL_REQUEST_TARGET=FORBIDDEN_BY_DEFAULT
BASE_UPDATE_FAT32_STAGING_PROOF=PASS_DISPOSABLE_CI
```

GitHub Actions remains the current build/proof executor; repository recipes are source authority. Kernel/build reproducibility, Action pinning and deterministic real-`system/` bundling remain CI-proven. The current A/B base staging code is also exercised on a disposable FAT32 loop image: the proof preserves current/recovery entries and the active slot, writes and verifies the inactive candidate, unmounts, runs read-only `fsck.vfat`, remounts and re-verifies bytes. That proof is explicitly filesystem-staging-only: it does not exercise canonical release trust, authorize physical writes, activate a candidate or prove notebook boot. CI proof does not authorize destructive physical writes or substitute for hardware validation.

## Physical architecture

The capacity-independent bootstrap seed and the current transitional USB prepared by Creator are different artifacts and must not be collapsed into one partition count:

```text
BOOTSTRAP_SEED_PARTITIONS=2
BOOTSTRAP_SEED_PARTITION_NAMES=ORDAX-ESP,ORDAX
SEED_PARTITION_1_FILESYSTEM=FAT32
SEED_PARTITION_2_FILESYSTEM=EXT4
PREPARED_USB_PARTITIONS=3
PREPARED_USB_PARTITION_NAMES=ORDAX-ESP,ORDAX,ORDAX-DATA
PREPARED_PARTITION_1_FILESYSTEM=FAT32
PREPARED_PARTITION_2_FILESYSTEM=EXT4
PREPARED_PARTITION_3_FILESYSTEM=EXFAT
SEPARATE_HOME_PARTITION=NO
LEGACY_ORDAX_PLATFORM_PARTITION=FORBIDDEN
LEGACY_ORDAX_HOME_PARTITION=FORBIDDEN
```

`docs/contracts/physical-media.json` is authoritative for the two-partition capacity-independent seed (`ORDAX-ESP` + `ORDAX`). `docs/contracts/physical-prepared-media.json` is authoritative for the current **transitional Owner/Development** prepared USB (`ORDAX-ESP` + bounded `ORDAX` + target-capacity-specific `ORDAX-DATA`). These counts describe different validation artifacts and are not the final Stable/MVP layout. The legacy/transitional release tree remains validation-only and must not become the public MVP default.

The durable MVP target is portable USB v2:

```text
ORDAX-ESP   FAT32
ORDAX-DATA  exFAT
  -> .ordax/base/stable-base.erofs
  -> .ordax/releases/<commit>/system.erofs
  -> .ordax/releases/<commit>/surface-runtime.sha256
  -> .ordax/runtimes/sha256/<runtime-sha256>/native-surface-runtime.erofs
  -> .ordax/state/persistent-state.img   # ext4-in-file
```

Mutable activation authority (`current`, `known-good`, `candidate`) lives inside the ext4 persistent-state image, never as a mutable exFAT symlink/pointer. Portable v2 remains a compatibility release shape; the current Stable/MVP candidate uses signed `release-manifest/3`, binding both `system.erofs` and the content-addressed Surface runtime. The Stable Base remains a separate immutable minimal OS EROFS. The fixed initramfs candidate owns exact release selection, capsule/Base verification, system/runtime EROFS mounts and the read-only-to-ephemeral OverlayFS handoff; signature authority remains in the bootstrap-owned release agent.

```text
PORTABLE_USB_V2_STORAGE_PROOF=PASS_CI_DISPOSABLE
PORTABLE_RELEASE_EROFS_REPRODUCIBLE=PASS_CI
PORTABLE_RELEASE_MANIFEST_V2_SIGN_VERIFY=PASS_CI_COMPATIBILITY
PORTABLE_RELEASE_MANIFEST_V3_SIGN_VERIFY=PASS_CI
PORTABLE_RELEASE_V3_CONTENT_ADDRESSED_RUNTIME=PASS_CI
PORTABLE_RELEASE_OFFLINE_EXACT_VERIFY=PASS_CI_V2_AND_V3
PORTABLE_MOUNT_HANDOFF_PROOF=PASS_CI_DISPOSABLE
PORTABLE_BOOTSTRAP_CAPSULE_REPRODUCIBLE=PASS_CI
PORTABLE_INITRAMFS_HELPERS=PASS_CI
PORTABLE_SURFACE_RUNTIME_APK_LOCK=PASS_CI_253_EXACT_PACKAGES
PORTABLE_SURFACE_RUNTIME_EROFS_REPRODUCIBLE=PASS_CI
PORTABLE_SURFACE_RUNTIME_EROFS_SHA256=170d306b38cfdbadba47a7548a6757a920ceaedea98697270aaa8ca4f4d8d038
PORTABLE_SURFACE_RUNTIME_BOOT_CONNECTED=YES_CANDIDATE_IMPLEMENTED
PORTABLE_STABLE_FIRST_SURFACE_OFFLINE_PROVEN=PENDING_CURRENT_HEAD_QEMU_UEFI
PORTABLE_STABLE_BOOT_APK_INSTALL_ALLOWED=NO
PORTABLE_SURFACE_RUNTIME_EPHEMERAL_OVERLAY=/run
PORTABLE_PINNED_INITRAMFS_COMPOSITION=PASS_CI_V2_BASELINE
PORTABLE_QEMU_DIRECT_KERNEL_BOOT=PASS_CI_V2_BASELINE
PORTABLE_QEMU_UEFI_BOOT=PASS_CI_V2_BASELINE_OVMF_NON_SECURE_BOOT
PORTABLE_RUNTIME_V3_QEMU_DIRECT_KERNEL_BOOT=PENDING_CURRENT_HEAD
PORTABLE_RUNTIME_V3_QEMU_UEFI_BOOT=PENDING_CURRENT_HEAD
PORTABLE_QEMU_NETWORK_REQUIRED=NO
PORTABLE_QEMU_PHYSICAL_TARGET_TOUCHED=NO
PORTABLE_QEMU_SECURE_BOOT=NO
PORTABLE_PHYSICAL_USB_BOOT=NO
PORTABLE_V2_PUBLIC_WRITER_ENABLED=NO
```

The offline Stable/MVP graphical runtime is a separate EROFS artifact with a full 253-package Alpine lock and repeat-digest proof. It deliberately excludes generated machine identity and Fontconfig caches from signed bytes. Release-manifest/3 now binds that runtime by SHA-256, Creator preseeds the content-addressed bytes, the candidate PID1 re-verifies v3 offline and mounts the runtime read-only beneath an ephemeral OverlayFS in `/run`, and the Stable launcher refuses boot-time `apk add` provisioning. **The implementation is connected; the fresh-USB graphical boot claim remains pending until the current-head QEMU/UEFI proof passes.**

Portable v2 itself has now crossed the CI boot-handoff gate with the final two-partition layout: the direct-kernel QEMU proof and the UEFI/OVMF + systemd-boot proof both reached `ORDAX_PORTABLE_V2_HANDOFF=VERIFIED` and `ORDAX_STABLE_INIT_HANDOFF=VERIFIED`, selected the exact `current` slot/source identity, ran with QEMU networking disabled, destroyed disposable guest state afterward and did not touch a physical target device. The UEFI proof uses non-Secure-Boot OVMF; **Secure Boot and physical USB boot remain unproven**.

CI proof remains distinct from physical boot evidence and does not authorize the public writer.

## Minimal bootstrap and canonical release path

The product bootstrap/release architecture remains distinct from the owner/development USB Git path.

```text
FULL_SYSTEM_PRESEEDED=NO
NORMAL_APPS_PRESEEDED=NO
REMOTE_CORE_PRESEEDED=NO
CONTROL_PLANE_PRESEEDED=NO
SSH_PRESEEDED=NO
BUILD_TOOLCHAIN_PRESEEDED=NO
KNOWN_GOOD_OFFLINE_BOOT_REQUIRED=YES
RELEASE_BUNDLE_TOOLING_IMPLEMENTED=YES
DETERMINISTIC_SYSTEM_TAR=PASS
REAL_REPOSITORY_SYSTEM_BUNDLE=PASS
RELEASE_MANIFEST_TOOLING_IMPLEMENTED=YES
RELEASE_SIGNING_TOOLING_IMPLEMENTED=YES
RELEASE_PIPELINE_CI=PASS
PRODUCTION_RELEASE_PUBLISHED=NO
```

The canonical release channel resolves `release-envelope.json`; the URL selects bytes and Ed25519 verification decides authenticity. The release acquisition code remains fail-closed with SHA-256 verification, exact source-commit binding, safe materialization, atomic activation and known-good preservation.

### Canonical release trust — unresolved

```text
RELEASE_TRUST_POLICY=RESOLVED
TRUST_POLICY_SCHEMA=prototype-ordax.release-trust-policy/1
CANONICAL_KEY_ID=ordax-prototype-release-v1
CANONICAL_KEY_MATERIAL_GENERATED=NO
PUBLIC_ANCHOR_PINNED=NO
RELEASE_TRUST=UNRESOLVED
PRIVATE_SIGNING_KEY_IN_GIT=FORBIDDEN
PRIVATE_SIGNING_KEY_IN_USB=FORBIDDEN
PRIVATE_KEY_CUSTODY_OWNER=repository-owner-developer
MINIMAL_BOOTSTRAP_ALL_ARTIFACTS_RESOLVED=NO
PHYSICAL_WRITE_ALLOWED=NO
```

The canonical private key must be generated and backed up outside Git according to `docs/RELEASE-TRUST-CEREMONY.md`; only the matching public trust document may enter source. CI/fixture keys never satisfy canonical trust.

## Creator and physical-write boundary

```text
CREATOR_CORE_IMPLEMENTED=YES
CREATOR_VERIFY_PAYLOAD_IMPLEMENTED=YES
CREATOR_STAGE_TREE=IMPLEMENTED_TRANSACTIONAL
CREATOR_DISPOSABLE_GPT_FILESYSTEM_PROOF=PASS
CREATOR_WINDOWS_TARGET_DISCOVERY=PASS
CREATOR_WINDOWS_SYSTEM_DISK_EXCLUSION=PASS
CREATOR_WINDOWS_NATIVE_RAW_DISK_BACKEND=PASS_TAGGED_UNBOUND
CREATOR_WINDOWS_RAW_BACKEND_BUILD_TAG=ordax_raw_backend
CREATOR_WINDOWS_RAW_BACKEND_BUILD_TAG_ISOLATION=PASS
CREATOR_WINDOWS_RAW_BACKEND_IN_PUBLIC_BUILD=NO
CREATOR_NATIVE_BACKEND_PUBLICLY_REACHABLE=NO
CREATOR_PUBLIC_PHYSICAL_APPLY_IMPLEMENTED=NO
PHYSICAL_WRITE_AUTHORIZED=NO
DESTRUCTIVE_AUTHORIZATION=NO
```

The internal Windows raw-disk implementation remains compile-time isolated and unreachable from the public Creator command. Nothing in the successful owner/development USB bring-up changes that destructive-write authorization boundary.

The byte-complete media workflow remains proven with ephemeral CI trust and disposable media only. That proof establishes composition and growth behavior; it does not establish canonical public trust or authorize a product-media write. The notebook development-USB boot is a separate physical proof and must not be used to collapse those boundaries.

## Recovery

```text
RECOVERY_ENTRY=YES
RECOVERY_ORDAX_MOUNT=READ_ONLY
RECOVERY_AUTOMATIC_NETWORK=NO
RECOVERY_SSH=NO
RECOVERY_AUTOMATIC_MUTATION=NO
RECOVERY_PHYSICAL_EXERCISE=PENDING_FINAL_VALIDATION
```

## Host independence and remote access

```text
WSL_REQUIRED=NO
QEMU_REQUIRED=NO
POWERSHELL_REQUIRED=NO
BASH_REQUIRED=NO
SPECIFIC_DEVELOPER_DESKTOP_OS_REQUIRED=NO
END_USER_KERNEL_TOOLCHAIN_REQUIRED=NO
THIN_HOST_ADAPTERS_ALLOWED=YES
SSH_REQUIRED=NO
REMOTE_CORE_REQUIRED=NO
CONTROL_PLANE_REQUIRED=NO
```

## Physical state

```text
OWNER_DEVELOPMENT_USB_PRESENT=YES
PHYSICAL_NOTEBOOK_BOOT_PROVEN=PASS_DEVELOPMENT_USB
PHYSICAL_NATIVE_GRAPHICS=PASS_DEVELOPMENT_USB
PHYSICAL_PRIMARY_INPUT=PASS_DEVELOPMENT_USB
PHYSICAL_NATIVE_RESTART=PASS_DEVELOPMENT_USB
PHYSICAL_NATIVE_SHUTDOWN=PASS_DEVELOPMENT_USB
PHYSICAL_LIVE_UPDATE=PASS_DEVELOPMENT_USB
PHYSICAL_GUARDIAN_SUPERVISOR=PASS_DEVELOPMENT_USB
PHYSICAL_RESCUE_CHANNEL=PASS_DEVELOPMENT_USB
PHYSICAL_TELEMETRY_RELAY=PASS_DEVELOPMENT_USB
CANONICAL_SIGNED_RELEASE_BOOT_PROVEN=NO
CANONICAL_NATIVE_DISK_INSTALL_PROVEN=NO
CREATOR_PUBLIC_PHYSICAL_APPLY_IMPLEMENTED=NO
RELEASE_TRUST=UNRESOLVED
DESTRUCTIVE_AUTHORIZATION=NO
```

Do not reinterpret `PASS_DEVELOPMENT_USB` as canonical release/install proof. The proven target today is the owner/development Git-first USB on the tested notebook.

## Deferred/final physical validation

The following are intentionally left for later/final hardware validation rather than blocking current product development:

```text
SURFACE_ONLY_NATIVE_HOST_RESTART_PHYSICAL=PASS_DEVELOPMENT_USB
SUSPEND_RESUME=PENDING_FINAL
AUDIO=PENDING_FINAL
GRAPHICS_ACCELERATION_QUALITY=PENDING_FINAL
LONG_RUN_STABILITY=PENDING_FINAL
RECOVERY_PHYSICAL_EXERCISE=PENDING_FINAL
BROADER_HARDWARE_COVERAGE=PENDING_FINAL
```

## Current priorities

1. prioritize the Stable/MVP **USB system path**: finish Portable v2 boot, canonical trust, offline graphical runtime, official non-Git acquisition, signed verification, staging, controlled activation, health, promotion and rollback without coupling ordinary app changes to a full system reboot;
2. keep the current first-party apps useful and coherent as Beta components, focusing app work on correctness, regression coverage and genuine MVP gaps; move an app toward production-independent packaging only when the signed `component-slot` path is actually ready to prove it;
3. continue hardening staged/transactional Owner/Development Git-first activation while keeping it explicitly separate from the Stable/MVP public update channel;
4. complete integrated Surface physical validation only after the source-controlled Portable v2/runtime path is ready; do not convert CI or an unexecuted runbook into physical PASS;
5. continue account/cloud preference and workspace continuity through neutral contracts without claiming remote transport before an authenticated provider exists;
6. complete the canonical Ed25519 release-trust ceremony only with the provenance-bound toolkit from a canonical `main` push, keeping private signing material outside Git/CI/chat;
7. keep all physical writers fail-closed until canonical trust, byte-complete media proof, exact target authorization and physical USB validation close;
8. leave suspend/resume, audio, acceleration-quality, long-run and broader-hardware exercises for final physical validation unless an MVP gate depends on them sooner.

## Autonomous recovery and observation boundary

```text
NORMAL_UPDATE_CONTROL=GIT_MAIN
BOUNDED_RECOVERY_CONTROL=GIT_ORDAX_RESCUE
OBSERVABILITY=SUPABASE_ORDAX_OS_RELAY
REMOTE_SHELL=NO
SUPABASE_COMMAND_CHANNEL=NO
GUARDIAN_NETWORK_ACCESS=NO
SUPERVISOR_GIT_ACCESS=YES
INTENTIONALLY_BAD_UPDATE_ROLLBACK_PHYSICAL_PROOF=PENDING
FULL_A_B_RUNTIME_ACTIVATION=NO
BASE_UPDATE_A_B_CONTRACT=DEFINED
BASE_UPDATE_FAT32_STAGING_PROOF=PASS_DISPOSABLE_CI
BASE_UPDATE_CANONICAL_TRUST_EXERCISED_BY_FAT32_PROOF=NO
BASE_UPDATE_PHYSICAL_HARDWARE_PROVEN=NO
BASE_UPDATE_PHYSICAL_WRITER=NO
```

The temporary Supabase project is an operational relay, not product authority. It may be migrated later without changing the device identity or telemetry contract. Git `main` remains product source authority; `ordax-rescue` remains a separate, deliberately narrow recovery path.

## Canonical documentation freshness

The Foundation regression suite compares this snapshot against structured owners for product version, first-party app versions/release modes and seed/transitional-media geometry. A source change that makes those values stale must fail CI until the canonical snapshot and nomenclature contract are updated in the same change. Portable v2 remains governed separately by `docs/contracts/portable-usb-v2.json`; transitional geometry must never be mistaken for the final public MVP target.

## Handoff rule

Any new AI/conversation must read `AGENTS.md`, this file and the canonical contracts before changing source. It must also reconcile current structured source with the snapshot before planning work from a historical statement. CI alone never proves physical boot, native graphics or destructive safety. For the tested owner/development USB notebook, physical native graphics/input/power/live-update claims are supported by `docs/evidence/physical-native-surface-2026-09-17.md`; those claims still do not promote CI trust, authorize physical mutation, prove canonical signed release acquisition or declare the product complete.
