#!/usr/bin/env python3
"""Regress exact-state development one-shot activation arming."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "system/services/base-update/dev_activation_arm.py"
AGENT = ROOT / "system/services/base-update/agent.sh"
CONTRACT = json.loads(
    (ROOT / "docs/contracts/base-update.json").read_text(encoding="utf-8")
)
SOURCE = "a" * 40


class DevelopmentActivationArmBoundaryTests(unittest.TestCase):
    def test_helper_requires_explicit_efivar_path_and_never_reboots(self):
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--efivarfs-root", type=Path, required=True)', text)
        self.assertIn('parser.add_argument("--efi-root", type=Path, required=True)', text)
        self.assertIn("_efivarfs.preflight(", text)
        self.assertIn("_activate.arm(", text)
        self.assertLess(
            text.index("_efivarfs.preflight("),
            text.index("_activate.arm("),
        )
        self.assertIn("_readonly.readonly_preflight(", text)
        self.assertIn('"ro,nosuid,nodev,noexec"', text)
        self.assertIn('"reboot_requested": False', text)
        self.assertIn('"runtime_owner_wiring_enabled": False', text)
        self.assertIn('"automatic_reboot_enabled": False', text)
        self.assertNotIn("reboot -f", text)
        self.assertNotIn("busybox reboot", text)
        self.assertNotIn("power-request", text)

    def test_mismatched_readiness_sha_fails_before_activation(self):
        spec = importlib.util.spec_from_file_location(
            "ordax_dev_activation_arm_boundary_test",
            HELPER,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        read_exact_sha = module._read_exact_sha
        error = module.DevelopmentActivationArmError

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "readiness-sha"
            path.write_text("b" * 40 + "\n", encoding="ascii")
            with self.assertRaisesRegex(error, "does not match candidate"):
                read_exact_sha(path, "activation readiness SHA state", SOURCE)

    def test_contract_keeps_runtime_owner_wiring_disabled(self):
        arm = CONTRACT["activation"]["development_runtime_arm"]
        self.assertEqual(
            arm["helper"],
            "system/services/base-update/dev_activation_arm.py",
        )
        self.assertEqual(
            arm["schema"],
            "prototype-ordax.dev-base-activation-arm/1",
        )
        for key in (
            "exact_staged_sha_required",
            "exact_readiness_sha_required",
            "readiness_state_required",
            "candidate_manifest_revalidated",
            "versioned_rootfs_revalidated",
            "live_esp_readonly_revalidation_required",
            "live_candidate_hash_revalidation_required",
            "esp_read_only_during_arm",
            "explicit_efivarfs_root_required",
            "only_loader_entry_oneshot_written",
            "disposable_efivarfs_only",
            "efivarfs_preflight_required",
            "fresh_efivarfs_preflight_immediately_before_write",
            "writable_efivarfs_required",
            "efivarfs_preflight_must_remain_non_authoritative",
            "efivarfs_preflight_variable_written_must_be_false",
            "explicit_efi_root_required",
        ):
            self.assertTrue(arm[key], key)
        self.assertFalse(arm["default_entry_changed"])
        self.assertFalse(arm["reboot_requested"])
        self.assertFalse(arm["automatic_reboot_enabled"])
        self.assertFalse(arm["runtime_owner_wiring_enabled"])
        self.assertTrue(arm["boot_counting_gate_merged"])
        self.assertTrue(arm["physical_efivarfs_evidence_required"])
        self.assertFalse(arm["real_efivarfs_proven"])
        self.assertFalse(arm["physical_notebook_proven"])
        self.assertEqual(
            arm["efivarfs_preflight_helper"],
            "system/services/base-update/efivarfs_preflight.py",
        )
        self.assertEqual(
            arm["efivarfs_preflight_schema"],
            "prototype-ordax.efivarfs-preflight/1",
        )
        self.assertEqual(
            arm["blocker"],
            "physical-efivarfs-evidence-required-before-runtime-owner-arm-wiring",
        )

    def test_persistent_owner_does_not_invoke_arm_helper(self):
        agent = AGENT.read_text(encoding="utf-8")
        self.assertNotIn("dev_activation_arm.py", agent)
        self.assertNotIn("prepare_dev_base_activation_arm", agent)


if __name__ == "__main__":
    unittest.main()
