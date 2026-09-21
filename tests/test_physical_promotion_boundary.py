#!/usr/bin/env python3
"""Regress separation between Portable layout policy and destructive authorization."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "creator" / "physical_promotion.py"
spec = importlib.util.spec_from_file_location("ordax_physical_promotion_test", MODULE_PATH)
promotion = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(promotion)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PhysicalPromotionBoundaryTests(unittest.TestCase):
    def make_ready_fixture(self, root: Path) -> None:
        trust = {
            "$schema": "prototype-ordax.release-trust/1",
            "key_id": "ordax-prototype-release-v1",
            "public_key_base64": base64.b64encode(bytes(range(32))).decode("ascii"),
        }
        trust_path = root / "bootstrap/trust/release-ed25519.json"
        write_json(trust_path, trust)
        trust_sha = sha256(trust_path)

        minimal = {
            "$schema": "prototype-ordax.minimal-bootstrap/4",
            "status": "canonical-bytes-resolved",
            "physical_write_allowed": False,
            "all_artifacts_resolved": True,
            "artifact_groups": [
                {
                    "id": "bootstrap-release-trust",
                    "partition": "ORDAX-ESP",
                    "source_owner": "bootstrap/trust",
                    "resolved": True,
                    "artifacts": [
                        {
                            "source_path": "bootstrap/trust/release-ed25519.json",
                            "target_path": "/ordax/bootstrap/trust/release-ed25519.json",
                            "sha256": trust_sha,
                            "mode": "0644",
                            "logical_owner": "bootstrap-release-trust",
                            "reason": "Canonical public Ed25519 release trust anchor",
                        }
                    ],
                }
            ],
        }
        minimal_path = root / "docs/contracts/minimal-bootstrap.json"
        write_json(minimal_path, minimal)

        portable = {
            "$schema": "prototype-ordax.portable-usb-v2/1",
            "product_scope": "mvp-usb-durable-storage-target",
            "physical_write_authorized": False,
            "physical_device_paths_allowed": False,
            "logical_sector_bytes": 512,
            "alignment_bytes": 1048576,
            "partitions": [
                {
                    "index": 1,
                    "name": "ORDAX-ESP",
                    "filesystem": "fat32",
                    "filesystem_label": "ORDAX-ESP",
                    "start_lba": 2048,
                    "size_bytes": 536870912,
                },
                {
                    "index": 2,
                    "name": "ORDAX-DATA",
                    "filesystem": "exfat",
                    "filesystem_label": "ORDAX-DATA",
                    "size_policy": "fill-all-remaining-usable-capacity",
                    "windows_visible": True,
                    "direct_overlayfs_upper": False,
                },
            ],
            "ordax_internal_layout": {
                "persistent_state_image": {
                    "path": ".ordax/state/persistent-state.img",
                    "filesystem": "ext4",
                    "filesystem_label": "ORDAX-STATE",
                    "mounted_through_loop_device_in_runtime": True,
                    "overlayfs_upper_owner": True,
                },
                "activation_state": {"not_stored_directly_on_exfat": True},
            },
        }
        portable_path = root / "docs/contracts/portable-usb-v2.json"
        write_json(portable_path, portable)

        creator_portable = {
            "$schema": "prototype-ordax.creator-portable-media-plan/1",
            "product_scope": "stable-mvp-usb-only",
            "artifact_count": 15,
            "partitions": ["ORDAX-ESP", "ORDAX-DATA"],
            "physical_write_authorized": False,
            "physical_device_paths_allowed": False,
            "disposable_materializer_implemented": True,
            "disposable_materializer_physical_device_allowed": False,
            "disposable_materializer_readback_verification": True,
            "physical_writer_v2_implemented": True,
            "application_planner": {
                "implemented": True,
                "consumes_exact_media_plan": True,
                "canonical_media_plan_sha256_bound": True,
                "host_neutral": True,
                "physical_device_bound": False,
                "physical_write_authorized": False,
                "public_promotion_allowed": False,
                "whole_disk_raw_image_required": False,
                "ordered_phases": [
                    "write-exact-two-partition-gpt",
                    "format-ORDAX-ESP-fat32",
                    "format-ORDAX-DATA-exfat",
                    "materialize-15-exact-artifacts",
                    "flush-and-sync",
                    "readback-sha256-and-size-for-15-artifacts",
                    "verify-gpt-filesystems-labels-and-capacity",
                ],
            },
            "surface_runtime_preseed": {
                "implemented": True,
                "image_artifact_id": "surface-runtime-image",
                "reference_artifact_id": "surface-runtime-ref",
                "content_addressed": True,
                "release_manifest_schema": "prototype-ordax.release-manifest/3",
                "physical_write_authorized": False,
            },
        }
        creator_path = root / "docs/contracts/creator-portable-media-plan.json"
        write_json(creator_path, creator_portable)

        policy = {
            "$schema": "prototype-ordax.release-trust-policy/1",
            "consumer_creator": {
                "generates_publisher_private_keys": False,
                "stores_publisher_private_keys": False,
                "requests_private_key_backup_from_end_user": False,
                "runs_release_trust_ceremony": False,
                "signature_verification_is_automatic": True,
            },
            "gates": {
                "key_material_generated": True,
                "public_anchor_pinned": True,
                "minimal_bootstrap_resolved": True,
                "physical_authorization_eligible": True,
            },
        }
        write_json(root / "docs/contracts/release-trust-policy.json", policy)

        auth = {
            "$schema": "prototype-ordax.physical-write-authorization/2",
            "status": "authorized",
            "physical_write_allowed": True,
            "explicit_owner_authorization": True,
            "source_repository": "washingtonmsdj/prototipo-ordax-os",
            "release_sequence": 1,
            "requirements": {
                name: True
                for name in promotion.REQUIRED_AUTHORIZATION_REQUIREMENTS
            },
            "bindings": {
                "minimal_bootstrap_sha256": sha256(minimal_path),
                "release_trust_sha256": trust_sha,
                "portable_usb_contract_sha256": sha256(portable_path),
                "creator_portable_media_contract_sha256": sha256(creator_path),
            },
        }
        write_json(root / "docs/contracts/physical-write-authorization.json", auth)

    def test_repository_stable_mvp_authorization_is_explicitly_unset(self):
        auth = json.loads(
            (ROOT / "docs/contracts/physical-write-authorization.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            auth["status"],
            "blocked-canonical-trust-pending",
        )
        self.assertFalse(auth["physical_write_allowed"])
        self.assertFalse(auth["explicit_owner_authorization"])
        self.assertEqual(auth["scope"], "first-real-stable-mvp-usb-proof")

    def test_ready_promotion_uses_only_portable_layout_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            status = promotion.evaluate(root)
            self.assertTrue(status["ready"], status["blockers"])
            self.assertTrue(status["pre_authorization_ready"])
            self.assertEqual(status["pre_authorization_blockers"], [])
            self.assertEqual(status["authorization_blockers"], [])
            self.assertFalse(status["owner_authorization_required"])
            self.assertTrue(status["authorized_candidate_materialization_allowed"])
            self.assertTrue(status["physical_authorization_bindings_resolved"])
            self.assertEqual(status["next_stage"], "authorized-candidate-materialization")
            self.assertEqual(
                status["portable_layout_authority"],
                "tools/creator/core/portable_media.go",
            )
            self.assertFalse(status["legacy_physical_media_contract_authoritative"])
            self.assertEqual(
                set(status["computed_bindings"]),
                {
                    "minimal_bootstrap_sha256",
                    "release_trust_sha256",
                    "portable_usb_contract_sha256",
                    "creator_portable_media_contract_sha256",
                },
            )

    def test_resolved_bindings_leave_only_explicit_authorization_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            auth_path = root / "docs/contracts/physical-write-authorization.json"
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            auth["status"] = "blocked-explicit-physical-authorization-pending"
            auth["physical_write_allowed"] = False
            auth["explicit_owner_authorization"] = False
            write_json(auth_path, auth)

            status = promotion.evaluate(root)

            self.assertFalse(status["ready"])
            self.assertTrue(status["pre_authorization_ready"], status["pre_authorization_blockers"])
            self.assertTrue(status["physical_authorization_bindings_resolved"])
            self.assertEqual(
                status["authorization_blockers"],
                ["explicit-physical-write-authorization-missing"],
            )
            self.assertTrue(status["owner_authorization_required"])
            self.assertEqual(status["next_stage"], "explicit-owner-authorization")
            self.assertFalse(status["authorized_candidate_materialization_allowed"])

    def test_pre_authorization_ready_does_not_authorize_destructive_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            auth_path = root / "docs/contracts/physical-write-authorization.json"
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            auth["status"] = "eligible-awaiting-explicit-authorization"
            auth["physical_write_allowed"] = False
            auth["bindings"] = {
                "minimal_bootstrap_sha256": None,
                "release_trust_sha256": None,
                "portable_usb_contract_sha256": None,
                "creator_portable_media_contract_sha256": None,
            }
            write_json(auth_path, auth)

            status = promotion.evaluate(root)

            self.assertFalse(status["ready"])
            self.assertTrue(status["pre_authorization_ready"], status["pre_authorization_blockers"])
            self.assertEqual(status["pre_authorization_blockers"], [])
            self.assertEqual(
                status["authorization_blockers"],
                [
                    "explicit-physical-write-authorization-missing",
                    "physical-authorization-bindings-unresolved",
                ],
            )
            self.assertTrue(status["owner_authorization_required"])
            self.assertFalse(status["authorized_candidate_materialization_allowed"])
            self.assertEqual(status["next_stage"], "explicit-owner-authorization")

    def test_legacy_ordax_ext4_contract_cannot_satisfy_portable_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            portable_path = root / "docs/contracts/portable-usb-v2.json"
            auth_path = root / "docs/contracts/physical-write-authorization.json"
            portable = json.loads(portable_path.read_text(encoding="utf-8"))
            portable["partitions"][1] = {
                "index": 2,
                "name": "ORDAX",
                "filesystem": "ext4",
                "filesystem_label": "ORDAX",
                "size_policy": "fill-all-remaining-usable-capacity",
                "windows_visible": False,
                "direct_overlayfs_upper": True,
            }
            write_json(portable_path, portable)
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            auth["bindings"]["portable_usb_contract_sha256"] = sha256(portable_path)
            write_json(auth_path, auth)
            status = promotion.evaluate(root)
            self.assertFalse(status["ready"])
            self.assertFalse(status["pre_authorization_ready"])
            self.assertIn("portable-usb-contract-invalid", status["pre_authorization_blockers"])
            self.assertIn("portable-usb-contract-invalid", status["blockers"])

    def test_portable_writer_must_be_implemented_before_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            creator_path = root / "docs/contracts/creator-portable-media-plan.json"
            auth_path = root / "docs/contracts/physical-write-authorization.json"
            creator = json.loads(creator_path.read_text(encoding="utf-8"))
            creator["physical_writer_v2_implemented"] = False
            write_json(creator_path, creator)
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            auth["bindings"]["creator_portable_media_contract_sha256"] = sha256(creator_path)
            write_json(auth_path, auth)
            status = promotion.evaluate(root)
            self.assertFalse(status["ready"])
            self.assertIn("portable-physical-writer-not-implemented", status["blockers"])

    def test_trust_policy_rejects_duplicate_destructive_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            policy_path = root / "docs/contracts/release-trust-policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["gates"]["physical_write_allowed"] = False
            write_json(policy_path, policy)
            status = promotion.evaluate(root)
            self.assertFalse(status["ready"])
            self.assertIn(
                "release-trust-policy-gates-not-authorized",
                status["blockers"],
            )

    def test_payload_level_destructive_flag_is_rejected_even_with_valid_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_ready_fixture(root)
            minimal_path = root / "docs/contracts/minimal-bootstrap.json"
            auth_path = root / "docs/contracts/physical-write-authorization.json"
            minimal = json.loads(minimal_path.read_text(encoding="utf-8"))
            minimal["physical_write_allowed"] = True
            write_json(minimal_path, minimal)
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            auth["bindings"]["minimal_bootstrap_sha256"] = sha256(minimal_path)
            write_json(auth_path, auth)
            status = promotion.evaluate(root)
            self.assertFalse(status["ready"])
            self.assertIn(
                "minimal-bootstrap-must-remain-non-destructive",
                status["blockers"],
            )


if __name__ == "__main__":
    unittest.main()
