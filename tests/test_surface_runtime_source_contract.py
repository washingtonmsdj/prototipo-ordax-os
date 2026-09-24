import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "bootstrap/surface-runtime/source.json"
DISCOVERY = ROOT / "bootstrap/surface-runtime/discover_lock.py"
BUILDER = ROOT / "bootstrap/surface-runtime/build.py"
WORKFLOW = ROOT / ".github" / "workflows" / "surface-runtime-lock-discovery.yml"
SURFACE = ROOT / "system/surface/bin/ordax-surface"


class SurfaceRuntimeSourceContractTests(unittest.TestCase):
    def test_candidate_requires_offline_first_boot_and_remains_unpromotable(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.surface-runtime-source/1")
        self.assertEqual(contract["status"], "candidate-not-promotable")
        self.assertEqual(contract["product_scope"], "stable-mvp-usb-only")
        self.assertTrue(contract["first_boot_offline_required"])
        self.assertFalse(contract["network_package_install_during_stable_boot_allowed"])
        self.assertTrue(contract["apk_package_versions_pinned"])
        self.assertIsInstance(contract["apk_package_lock"], dict)
        self.assertEqual(contract["apk_package_lock_count"], len(contract["apk_package_lock"]))
        self.assertEqual(contract["apk_package_lock_count"], 253)
        self.assertFalse(contract["artifact"]["physical_artifact_authorized"])
        self.assertTrue(
            contract["artifact"]["portable_v3_boot_handoff_candidate_connected"]
        )
        self.assertFalse(contract["artifact"]["physical_boot_connected"])
        self.assertEqual(
            contract["artifact"]["release_manifest_schema"],
            "prototype-ordax.release-manifest/3",
        )
        self.assertIn(
            "prove-stable-first-surface-boot-with-network-disabled-on-current-head",
            contract["promotion_blockers"],
        )

    def test_candidate_reuses_exact_stable_base_alpine_identity(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        stable = json.loads((ROOT / "bootstrap/stable-base/source.json").read_text(encoding="utf-8"))
        for field in ("version", "branch", "arch", "archive_sha256"):
            self.assertEqual(contract["alpine"][field], stable["alpine"][field])

    def test_discovery_is_lock_only_and_forbids_physical_promotion(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"status": "verified-pinned-lock" if isinstance(expected_lock, dict) else "discovered-not-promotable"', text)
        self.assertIn("resolved package lock differs from committed candidate lock", text)
        self.assertIn('"drift-detected-not-promotable"', text)
        self.assertIn('result["drift"] = drift', text)
        self.assertIn("full drift report was written before failing closed", text)
        self.assertIn('"physical_artifact_created": False', text)
        self.assertIn('"physical_write_authorized": False', text)
        self.assertIn('"portable_v3_boot_handoff_candidate_connected": True', text)
        self.assertIn('"physical_boot_connected": False', text)
        self.assertNotIn("/dev/sd", text)
        self.assertNotIn("/dev/nvme", text)


    def test_workflow_uploads_drift_report_even_when_revalidation_fails(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("- name: Upload proof metadata only\n        if: always()", text)
        self.assertIn("surface-runtime-lock.json", text)

    def test_builder_is_fail_closed_until_reviewed_lock_is_committed(self):
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('status") != "candidate-not-promotable"', text)
        self.assertIn('apk_package_versions_pinned") is not True', text)
        self.assertIn("Surface runtime cannot build before reviewed APK lock is committed", text)
        self.assertIn('"physical_artifact_authorized": False', text)
        self.assertIn('"portable_v3_boot_handoff_candidate_connected": True', text)
        self.assertIn('"physical_boot_connected": False', text)


    def test_immutable_runtime_excludes_device_identity_and_derived_font_cache(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        generated = contract["runtime_generated_state"]
        self.assertFalse(generated["machine_identity_baked_into_image"])
        self.assertFalse(generated["fontconfig_cache_baked_into_image"])
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('for relative in ("etc/machine-id", "var/lib/dbus/machine-id")', text)
        self.assertIn('cache = rootfs / "var/cache/fontconfig"', text)
        self.assertIn("prune_generated_runtime_state(rootfs)", text)

    def test_existing_owner_runtime_path_is_not_silently_removed(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn("install_runtime()", surface)
        self.assertIn("run_bounded_apk", surface)
        self.assertIn('if [ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]', surface)


if __name__ == "__main__":
    unittest.main()
