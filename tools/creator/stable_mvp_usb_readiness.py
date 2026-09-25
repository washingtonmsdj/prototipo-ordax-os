#!/usr/bin/env python3
"""Report the single read-only Stable/MVP USB release-readiness state.

This command composes the canonical Nova OrdaX source audit with the physical
promotion preflight. It never reads private signing-key contents, selects a
physical device, records owner consent, invokes a writer, materializes a
destructive candidate, or performs a physical write.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = Path(__file__).with_name("pre_usb_nova_ordax_audit.py")
PROMOTION_PATH = Path(__file__).with_name("physical_promotion.py")
STATUS_SCHEMA = "prototype-ordax.stable-mvp-usb-readiness/1"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load("ordax_pre_usb_readiness_audit", AUDIT_PATH)
promotion = _load("ordax_physical_promotion_readiness", PROMOTION_PATH)


def classify(
    source_status: dict[str, Any],
    promotion_status: dict[str, Any],
) -> str:
    if source_status.get("source_ready") is not True:
        return "source-blocked"
    if promotion_status.get("canonical_v4_release_proof_valid") is not True:
        return "canonical-v4-release-proof-pending"
    if promotion_status.get("pre_authorization_ready") is not True:
        return "promotion-pre-authorization-blocked"
    if promotion_status.get("ready") is True:
        if promotion_status.get("authorized_candidate_materialization_allowed") is not True:
            return "promotion-state-inconsistent"
        return "authorized-candidate-ready-for-separate-physical-flow"
    if promotion_status.get("owner_authorization_required") is True:
        return "explicit-owner-authorization-pending"
    return "promotion-state-inconsistent"


def evaluate(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    source_status = audit.evaluate(root)
    promotion_status = promotion.evaluate(root)
    stage = classify(source_status, promotion_status)

    source_blockers = list(source_status.get("blockers", []))
    promotion_blockers = list(promotion_status.get("blockers", []))
    blockers = sorted(set([*source_blockers, *promotion_blockers]))

    return {
        "$schema": STATUS_SCHEMA,
        "status": "ready" if stage == "authorized-candidate-ready-for-separate-physical-flow" else "blocked",
        "stage": stage,
        "source_ready": source_status.get("source_ready") is True,
        "pre_usb_source_audit_status": source_status.get("status"),
        "canonical_v4_release_proof_valid": promotion_status.get("canonical_v4_release_proof_valid") is True,
        "canonical_v4_release_binding_resolved": promotion_status.get("canonical_v4_release_binding_resolved") is True,
        "pre_authorization_ready": promotion_status.get("pre_authorization_ready") is True,
        "owner_authorization_required": promotion_status.get("owner_authorization_required") is True,
        "owner_authorization_recorded": promotion_status.get("ready") is True,
        "authorized_candidate_materialization_allowed": promotion_status.get("authorized_candidate_materialization_allowed") is True,
        "next_stage": promotion_status.get("next_stage"),
        "release_sequence": promotion_status.get("release_sequence"),
        "canonical_v4_release_source_commit": promotion_status.get("canonical_v4_release_source_commit"),
        "blockers": blockers,
        "physical_target_selected": False,
        "target_specific_destructive_confirmation_recorded": False,
        "writer_invoked": False,
        "physical_write_performed": False,
        "physical_proof_completed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--require-authorized-candidate", action="store_true")
    args = parser.parse_args()

    try:
        status = evaluate(args.repo_root)
    except Exception as exc:
        status = {
            "$schema": STATUS_SCHEMA,
            "status": "blocked",
            "stage": "readiness-evaluation-failed",
            "blockers": ["readiness-evaluation-failed"],
            "error": str(exc),
            "physical_target_selected": False,
            "writer_invoked": False,
            "physical_write_performed": False,
            "physical_proof_completed": False,
        }

    print(json.dumps(status, indent=2, sort_keys=True))
    if args.require_authorized_candidate and status.get("status") != "ready":
        return 2
    return 0 if status.get("stage") != "readiness-evaluation-failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
