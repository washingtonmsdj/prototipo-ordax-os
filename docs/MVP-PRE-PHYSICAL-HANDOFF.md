# OrdaX MVP — pre-physical handoff

Status: CANONICAL EXECUTION HANDOFF BEFORE FIRST STABLE/MVP PHYSICAL USB

This document narrows the final pre-physical boundary. It does not authorize a USB write and does not replace `MVP.md`, `docs/CURRENT-STATE.md`, `docs/PROMOTION-GATES.md`, the physical authorization contract, or hardware evidence.

## Current boundary

The current repository state is intentionally split into separate proofs:

```text
PRE_USB_PRODUCT_SOURCE=PASS
CANONICAL_V4_RELEASE_CANDIDATE_PROOF=PASS
CANONICAL_V4_RELEASE_PROOF_BINDING=PASS
PHYSICAL_WRITE_AUTHORIZATION=PASS_EXPLICIT_OWNER_CONSENT_BOUND_CONTEXT
PHYSICAL_TARGET_SELECTED=NO
PHYSICAL_WRITE_PERFORMED=NO
CANONICAL_STABLE_GRAPHICAL_SESSION=PENDING_PHYSICAL_PROOF
CANONICAL_SYSTEM_RUNTIME=PENDING_PHYSICAL_PROOF
STABLE_CHANNEL_PUBLICATION=PENDING_AFTER_PHYSICAL_PROOF
```

`PASS` in source or CI never upgrades a physical gate implicitly.

## Interpreting broad roll-up markers

`docs/CURRENT-STATE.md` still contains the broad roll-ups `GRAPHICAL_SURFACE_COMPLETE=NO` and `CANONICAL_SYSTEM_RUNTIME_COMPLETE=NO`. Those lines must not be read as saying that the shared graphical source or the pre-USB product implementation is missing.

Their current operational meaning is narrower:

- the shared Surface source, Native composition, Stable v4 payload and pre-USB product closure are implemented and source/CI-proven within their documented scopes;
- the Owner/Development graphical path has physical evidence;
- the **canonical Stable/MVP physical graphical session** is not yet proven;
- cold-health, known-good persistence, offline reboot and physical rollback/recovery are not yet proven on the canonical Stable/MVP USB;
- therefore the complete canonical runtime remains physically gated.

The authoritative separation is the one in `docs/PROMOTION-GATES.md`: Gate 9 keeps `MVP_SURFACE_SMOKE_PHYSICAL` and `CANONICAL_STABLE_GRAPHICAL_MODE` pending, while the source and Owner/Development facts remain independently recorded.

## Ordered remaining gates

At the current `authorized-candidate-ready-for-separate-physical-flow` stage, owner authorization is complete. The remaining gates are:

1. select the physical USB and revalidate its live identity immediately before destructive work;
2. require target-specific destructive confirmation and Windows UAC;
3. execute the physical write and verify all 17 canonical artifacts by exact SHA-256 and size/readback;
4. boot the canonical Stable/MVP USB on the target notebook and complete the OOBE -> Surface -> first-party-app smoke tour;
5. prove real cold-health, commit `current/known-good`, reboot offline and confirm the known-good boot;
6. exercise a broken candidate and prove physical rollback/recovery without losing the known-good release;
7. only after the required physical evidence, promote the approved release into the Stable public channel/catalog.

Authorization is now recorded. It does not select media, confirm a target, invoke the writer, establish physical proof, or publish a Stable release.

## Read-only status command

Use:

```text
python tools/creator/stable_mvp_usb_readiness.py
```

The output separates:

- `pre_usb_product_source_complete`;
- the signed/bound canonical v4 candidate proof;
- owner authorization state;
- source-versus-physical `proof_boundaries`;
- ordered `remaining_gates`;
- explicit false values for target selection, writer invocation, physical write and physical proof.

To use the same command as a fail-closed prerequisite for the later operator flow:

```text
python tools/creator/stable_mvp_usb_readiness.py --require-authorized-candidate
```

That option may succeed only after the authorization contract is ready. Success still means **authorized candidate ready for a separate physical flow**, never “physical proof complete”.

## First-MVP operator readiness split

For the actual operator handoff, use the aggregate read-only command:

```text
python tools/ops/first_mvp_operator_readiness.py
```

It deliberately keeps three concerns independent:

- `first_usb`: whether the source-authorized physical writer path is ready for the offline `creator-physical` signing/publication handoff before any USB target is selected;
- `official_creator`: whether the end-user Windows Creator has its separate Authenticode publisher identity/certificate policy configured and is ready for public distribution;
- `native_installation`: whether post-MVP internal-disk foundations may exist in source while remaining hidden, disabled and fail-closed in the MVP.

An unconfigured Authenticode identity for the public Creator must remain a publication blocker for the public Creator, but it must **not** be misreported as a blocker for the already-authorized first physical USB proof. The first USB path still requires the purpose-bound physical writer to be signed with the canonical Ed25519 release key and deliberately published under the `creator-physical` publisher channel before a physical target is selected.

Use the fail-closed operator prerequisite form when preparing that handoff:

```text
python tools/ops/first_mvp_operator_readiness.py --require-first-usb-handoff
```

This command never reads private-key contents, creates a signature, publishes a release, selects media, invokes the writer, records target confirmation, writes the USB or writes an internal disk.

## Public Creator boundary

The internal/tagged physical writer may remain implemented while the normal public Creator keeps destructive apply disabled. Do not expose public physical apply merely because owner authorization exists. Public exposure is a later product-promotion decision and must preserve target filtering, system-disk exclusion, live revalidation, target-specific confirmation, UAC and exact readback.

The official Creator publication boundary is stricter than the first owner-operated USB proof: `docs/contracts/creator-code-signing.json` must be explicitly configured with the reviewed Authenticode publisher identity, pinned leaf certificate SHA-256 and custody provider before public distribution is allowed. Keeping that capability hidden or fail-closed in the MVP is intentional product gating, not unfinished storage architecture.

## Stable publication boundary

The current canonical v4 candidate is a prerelease. Stable/`latest` publication must not be used as a shortcut around the first canonical physical proof. The final public catalog must point only to a release whose physical evidence matches the documented MVP support scope.
