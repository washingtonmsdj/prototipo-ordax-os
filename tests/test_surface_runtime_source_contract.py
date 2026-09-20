import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "bootstrap/surface-runtime/source.json"
DISCOVERY = ROOT / "bootstrap/surface-runtime/discover_lock.py"
SURFACE = ROOT / "system/surface/bin/ordax-surface"


class SurfaceRuntimeSourceContractTests(unittest.TestCase):
    def test_candidate_requires_offline_first_boot_and_remains_unpromotable(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.surface-runtime-source/1")
        self.assertEqual(contract["status"], "lock-discovery-required")
        self.assertEqual(contract["product_scope"], "stable-mvp-usb-only")
        self.assertTrue(contract["first_boot_offline_required"])
        self.assertFalse(contract["network_package_install_during_stable_boot_allowed"])
        self.assertFalse(contract["apk_package_versions_pinned"])
        self.assertIsNone(contract["apk_package_lock"])
        self.assertFalse(contract["artifact"]["physical_artifact_authorized"])
        self.assertFalse(contract["artifact"]["portable_v2_boot_connected"])
        self.assertIn("prove-stable-first-surface-boot-with-network-disabled", contract["promotion_blockers"])

    def test_candidate_reuses_exact_stable_base_alpine_identity(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        stable = json.loads((ROOT / "bootstrap/stable-base/source.json").read_text(encoding="utf-8"))
        for field in ("version", "branch", "arch", "archive_sha256"):
            self.assertEqual(contract["alpine"][field], stable["alpine"][field])

    def test_discovery_is_lock_only_and_forbids_physical_promotion(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"status": "discovered-not-promotable"', text)
        self.assertIn('"physical_artifact_created": False', text)
        self.assertIn('"physical_write_authorized": False', text)
        self.assertIn('"portable_v2_boot_connected": False', text)
        self.assertNotIn("/dev/sd", text)
        self.assertNotIn("/dev/nvme", text)

    def test_existing_owner_runtime_path_is_not_silently_removed(self):
        surface = SURFACE.read_text(encoding="utf-8")
        self.assertIn("install_runtime()", surface)
        self.assertIn("run_bounded_apk", surface)
        self.assertIn('if [ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]', surface)


if __name__ == "__main__":
    unittest.main()
