# Account Sync and Plans

Status: CANONICAL FOR PROTOTYPE

## One identity

An OrdaX user has one account across every supported product mode:

```text
Web
Android / iPhone / iPad
Desktop
USB
Native
```

The account owns identity, entitlements and synchronized user state. A device owns only device-local state and secrets.

## Spaces and professional Profile Packs

The account profile identifies the user. **Spaces** organize contexts of work, projects, memory and future collaboration.

A professional profile such as Developer, Creator, Business or Legal is modeled as a versioned **Profile Pack applied to a Space**, not as another user identity and not as another operating system.

Profile Pack categories are not paid merely because of their name. Future plans may monetize measurable ecosystem value such as additional active Spaces, shared membership, cloud memory/history, sync/backup capacity, external-model compute, connectors, automations and support.

The pre-MVP foundation carries a **provisional two-private-Space default** for the free experience. This is a product-capacity default, not a frozen price or final commercial tier.

Profile Packs may compose apps, templates, knowledge-source policy and Intelligence defaults, but they cannot grant privileges, bypass app signature verification or bypass entitlement checks.

## Cross-device continuity — backend v1 + Web source integration implemented

The first account-scoped synchronization backend is now applied to the dedicated `ordax-control-plane` project. It provides owner-scoped RLS, stable object IDs, server revisions, idempotent mutation keys, explicit tombstones and optimistic conflict detection through `ordax_apply_sync_mutation_v1`. This is the real backend foundation for the same account to carry approved state between devices.

The Web source now has an end-to-end OrdaX-owned transport boundary for `appearance`, portable accessibility preferences and portable workspace metadata. It uses the real account session without exposing provider tokens to Surface JavaScript. USB/Native and Mobile still lack their final secure transport/device-session integration, so synchronization remains **Em breve** in public copy and is not yet advertised as a released MVP capability.

The architecture remains prepared for future synchronized state such as:

- appearance and theme;
- preferences;
- workspace metadata;
- app-state metadata that is safe to move between devices;
- explicitly selected cloud-backed user content.

The long-term target is that one identity can continue safely across supported experiences without account silos. This is a future service objective, not an MVP availability claim.

## Never-sync boundary

The following classes remain local regardless of plan:

- private device keys;
- machine identity secrets;
- hardware-specific drivers;
- raw disk state;
- ephemeral caches;
- credentials that are intentionally device-bound;
- privileged recovery material whose security contract requires locality.

A paid plan never turns device-private security material into cloud-synchronized data.

## Offline-first behavior

Clients may continue working with locally available data while offline. Synchronization resumes when connectivity returns.

Before production promotion the sync engine must define deterministic conflict handling for concurrent changes. Silent last-writer-wins for all data classes is not an acceptable universal policy.

The scalable sync boundary is now machine-readable in `docs/contracts/sync-model.json`. It requires stable object IDs, versioned object schemas, server revisions, idempotent mutation keys, explicit deletion tombstones, opaque incremental cursors and support for a safe full resync. Client wall-clock time is not authoritative for conflict resolution.

Conflict algorithms are deliberately not frozen globally. Each data class or content type owns a deterministic, versioned resolver. This allows richer future models without rewriting every client and prevents a simplistic global last-writer-wins rule from becoming permanent architecture.

## Provider independence

Sync/domain semantics belong to `system/services/sync`, not to a database vendor, cloud provider or platform adapter. A future backend may use any suitable durable store, queue or object storage combination as long as it satisfies the domain contract.

Clients consume OrdaX object/revision semantics rather than database rows or provider-specific identifiers. Changing the backend therefore must not require a client migration solely because infrastructure changed.

Platform adapters own secure token storage, lifecycle/background integration and transport plumbing. They cannot redefine data classification, conflict policy, entitlements or never-sync boundaries.

## Security

Synchronization requires:

- encrypted transport;
- server-side authorization for every user-scoped object;
- device/session revocation;
- bounded token lifetime and secure local token storage;
- explicit data classification;
- auditable entitlement checks for premium capabilities;
- no client-side trust in a locally claimed paid plan.

Platform biometric APIs may protect local session access, but biometrics do not replace canonical account authentication or server authorization.

## Monetization architecture — commercial policy deferred

No billing, price table, commercial tier name or device-count paywall is defined for the MVP.

The account/domain architecture keeps an entitlement boundary so future services can be authorized server-side without fragmenting identity. Potential value-bearing categories include synchronization capacity/history, cloud storage, backup/restore, PC/Web/Mobile continuity, collaboration, premium compute/features and enhanced recovery/support.

The direction is to charge for **ecosystem value and service capacity**, not to impose an arbitrary fee merely because a user connects a second device.


## Downgrade safety

A plan downgrade must not silently delete user data. If the stored amount exceeds the new quota, the service should enter a documented limited state, for example retaining existing data while blocking new uploads until usage is reduced or the plan is upgraded.

Exact retention and grace-period policy is a later commercial decision, but destructive surprise is forbidden.

## Devices

The MVP defines **no commercial device-count limit**.

A future device registry exists for session security, revocation, continuity and device management. It distinguishes devices/sessions without synchronizing device-private keys. Any future commercial limit requires a separate explicit decision; charging merely for a second device is not the current direction.

## Data ownership and portability

Plan design must not make the user's own synchronized data inaccessible solely because a premium feature expired. Export/delete/account controls should remain account-level capabilities independent of the client used to invoke them.

## Architecture boundary

Shared services own sync semantics. Platform adapters own transport integration, secure storage, background scheduling and OS-specific lifecycle details.

```text
system/services/sync
        |
        +-> web adapter
        +-> mobile adapter (Android/iOS)
        +-> desktop adapter
        +-> native adapter
```

No platform gets its own incompatible synchronization model.
