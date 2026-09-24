#!/usr/bin/env python3
"""Regress the Creator portable-v2 disposable prepared-media materializer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/creator/proof/portable_prepared_media.py"
CONTRACT = ROOT / "docs/contracts/creator-portable-media-plan.json"

spec = importlib.util.spec_from_file_location("ordax_portable_prepared_media", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class CreatorPortablePreparedMediaTests(unittest.TestCase):
    def test_contract_keeps_materializer_nonphysical(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertTrue(contract["disposable_materializer_implemented"])
        self.assertFalse(contract["disposable_materializer_physical_device_allowed"])
        self.assertTrue(contract["disposable_materializer_readback_verification"])
        self.assertEqual(contract["artifact_count"], 17)
        runtime = contract["surface_runtime_preseed"]
        self.assertTrue(runtime["implemented"])
        self.assertTrue(runtime["content_addressed"])
        self.assertFalse(runtime["physical_write_authorized"])
        self.assertIn("/.ordax/runtimes/sha256/", runtime["image_target"])
        self.assertTrue(runtime["reference_target"].endswith("/surface-runtime.sha256"))
        self.assertEqual(runtime["release_manifest_schema"], "prototype-ordax.release-manifest/4")
        ai_runtime = contract["local_ai_runtime_preseed"]
        self.assertTrue(ai_runtime["implemented"])
        self.assertTrue(ai_runtime["content_addressed"])
        self.assertFalse(ai_runtime["physical_write_authorized"])
        self.assertIn("/.ordax/ai-runtimes/sha256/", ai_runtime["image_target"])
        self.assertTrue(ai_runtime["reference_target"].endswith("/local-ai-runtime.sha256"))
        self.assertEqual(ai_runtime["release_manifest_schema"], "prototype-ordax.release-manifest/4")
        self.assertTrue(contract["physical_writer_v2_implemented"])
        writer = contract["physical_writer_v2"]
        self.assertTrue(writer["implemented"])
        self.assertEqual(writer["build_tag"], "ordax_raw_backend")
        self.assertEqual(writer["exact_operation_count"], 39)
        self.assertEqual(writer["exact_artifact_count"], 17)
        self.assertTrue(writer["readback_sha256_and_size_per_artifact"])
        self.assertTrue(writer["writer_source_commit_provenance_separate"])
        self.assertTrue(writer["canonical_release_source_commit_from_authorization_binding"])
        self.assertTrue(writer["portable_plan_source_commit_must_equal_canonical_release_source_commit"])
        self.assertFalse(writer["whole_disk_raw_image_required"])
        self.assertFalse(writer["public_creator_reachable"])
        self.assertFalse(writer["physical_write_authorized"])
        self.assertFalse(writer["public_mvp_default_enabled"])
        self.assertFalse(contract["public_mvp_default_enabled"])
        application = contract["application_planner"]
        self.assertTrue(application["implemented"])
        self.assertTrue(application["host_neutral"])
        self.assertFalse(application["physical_device_bound"])
        self.assertFalse(application["physical_write_authorized"])
        self.assertFalse(application["public_promotion_allowed"])
        self.assertFalse(application["whole_disk_raw_image_required"])
        self.assertTrue(application["canonical_media_plan_sha256_bound"])

    def test_script_consumes_core_plan_targets_and_rejects_device_output(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('PLAN_SCHEMA = "prototype-ordax.portable-media-plan/1"', text)
        self.assertIn('artifact["target_path"]', text)
        self.assertIn('artifact["partition"]', text)
        self.assertIn('startswith("/dev/")', text)
        self.assertIn('"physical_target_device_touched": False', text)
        self.assertIn('"physical_write_authorized": False', text)
        self.assertNotIn("PlanPortableTargetStorage", text)
        self.assertNotIn("PhysicalDrive", text)

    def test_source_transport_must_match_core_hash_and_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "a"
            source.write_bytes(b"hello")
            plan = {
                "$schema": module.PLAN_SCHEMA,
                "profile": "portable-usb",
                "source_commit": "0" * 40,
                "target_bytes": 3 * 1024 * 1024 * 1024,
                "physical_write_authorized": False,
                "artifacts": [
                    {
                        "id": f"id-{index}",
                        "partition": "ORDAX-ESP" if index < 8 else "ORDAX-DATA",
                        "target_path": f"/file-{index}",
                        "sha256": module.sha256_file(source),
                        "size_bytes": source.stat().st_size,
                    }
                    for index in range(17)
                ],
            }
            parsed = module.load_plan(
                self._write_json(root / "plan.json", plan)
            )
            sources = [f"id-{index}={source}" for index in range(17)]
            result = module.parse_sources(sources, parsed)
            self.assertEqual(len(result), 17)

            source.write_bytes(b"tampered")
            with self.assertRaisesRegex(module.ProofError, "size mismatch|digest mismatch"):
                module.parse_sources(sources, parsed)

    def _write_json(self, path: Path, value: dict) -> Path:
        path.write_text(json.dumps(value), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
