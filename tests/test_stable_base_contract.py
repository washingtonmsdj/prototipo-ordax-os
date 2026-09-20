#!/usr/bin/env python3
"""Regress the Stable/MVP minimal OS base boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "bootstrap/stable-base/source.json"
BUILDER = ROOT / "bootstrap/stable-base/build.py"
INIT = ROOT / "bootstrap/stable-base/ordax-stable-init"
COMMON = ROOT / "bootstrap/base/alpine_core.py"


class StableBaseContractTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    def test_candidate_is_usb_only_and_not_promotable_yet(self):
        self.assertEqual(self.source["$schema"], "prototype-ordax.stable-base-source/1")
        self.assertEqual(self.source["status"], "candidate-not-promotable")
        self.assertEqual(self.source["product_scope"], "stable-mvp-usb-only")
        self.assertFalse(self.source["build"]["physical_artifact_authorized"])
        self.assertFalse(self.source["build"]["signed_update_integration_implemented"])
        self.assertFalse(self.source["build"]["qemu_boot_proven"])
        self.assertFalse(self.source["build"]["physical_boot_proven"])

    def test_stable_base_has_no_git_checkout_or_development_helpers(self):
        self.assertNotIn("git", self.source["packages"])
        self.assertFalse(self.source["git_client_allowed"])
        self.assertFalse(self.source["source_checkout_allowed"])
        self.assertFalse(self.source["development_helpers_allowed"])
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('"usr/bin/git"', text)
        self.assertIn('"usr/local/bin/ordax-pull"', text)
        self.assertIn('"sbin/ordax-dev-init"', text)
        self.assertIn("forbidden development path", text)
        self.assertNotIn("bootstrap/dev-base/ordax-pull", text)

    def test_shared_alpine_kernel_and_firmware_implementation_is_reused(self):
        build = self.source["build"]
        self.assertEqual(build["shared_alpine_core"], "bootstrap/base/alpine_core.py")
        self.assertEqual(build["shared_firmware_policy"], "bootstrap/base/firmware_policy.py")
        self.assertEqual(build["shared_runtime_policy"], "bootstrap/base/runtime_policy.py")
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn("CORE.select_module_members", text)
        self.assertIn("FIRMWARE.available_firmware_names", text)
        self.assertIn("RUNTIME.prune_build_only_runtime", text)

    def test_upstream_and_package_locks_are_explicit_promotion_blockers(self):
        alpine = self.source["alpine"]
        self.assertIsNone(alpine["archive_sha256"])
        self.assertEqual(alpine["archive_hash_pin_status"], "pending-from-verified-candidate")
        self.assertFalse(self.source["apk_package_versions_pinned"])
        self.assertEqual(self.source["apk_package_lock_status"], "pending-before-promotion")
        self.assertIn("pin-alpine-minirootfs-sha256", self.source["promotion_blockers"])
        self.assertIn("lock-exact-apk-package-versions", self.source["promotion_blockers"])

    def test_stable_base_is_complete_os_base_but_not_product_release(self):
        rootfs = self.source["rootfs"]
        self.assertEqual(rootfs["format"], "erofs")
        self.assertEqual(rootfs["artifact_name"], "stable-base.erofs")
        self.assertEqual(rootfs["target_path"], ".ordax/base/stable-base.erofs")
        self.assertTrue(rootfs["read_only"])
        self.assertTrue(rootfs["complete_minimal_os_userspace"])
        self.assertFalse(rootfs["product_system_tree_embedded"])
        self.assertFalse(rootfs["surface_runtime_embedded"])
        self.assertFalse(rootfs["mutable_state_embedded"])

    def test_stable_init_requires_verified_portable_identity(self):
        text = INIT.read_text(encoding="utf-8")
        self.assertIn('ORDAX_DISTRIBUTION_PROFILE:-}" = "stable-mvp"', text)
        self.assertIn('ORDAX_PRODUCT_MODE:-}" = "usb"', text)
        self.assertIn('ORDAX_STABLE_LAYOUT:-}" = "portable-v2"', text)
        self.assertIn('ORDAX_SOURCE_SHA', text)
        self.assertIn("[ -x /system/entrypoint ]", text)
        self.assertIn("exec /system/entrypoint", text)
        self.assertNotIn("git", text.lower())

    def test_common_module_selector_is_profile_neutral_with_dev_compatibility(self):
        text = COMMON.read_text(encoding="utf-8")
        self.assertIn("def select_module_members(", text)
        self.assertIn("def select_dev_module_members(", text)
        self.assertIn("WIFI_MODULE_BASENAMES", text)
        self.assertIn("DEV_MODULE_BASENAMES = WIFI_MODULE_BASENAMES", text)


if __name__ == "__main__":
    unittest.main()
