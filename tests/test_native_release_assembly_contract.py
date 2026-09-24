#!/usr/bin/env python3
"""Regression tests for the Native release assembly contract."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "docs" / "contracts" / "native-release-assembly.json").read_text(
        encoding="utf-8"
    )
)


class NativeReleaseAssemblyContractTests(unittest.TestCase):
    def test_contract_keeps_one_signed_system_tar_path(self):
        self.assertEqual(
            CONTRACT["$schema"],
            "prototype-ordax.native-release-assembly/2",
        )
        self.assertEqual(
            CONTRACT["recipe"],
            "tools/native-release-assembly/build.py",
        )
        output = CONTRACT["output"]
        self.assertEqual(
            output["helper_paths"],
            [
                "system/bin/ordax-native-install-targets",
                "system/bin/ordax-runtime-component-channel",
            ],
        )
        self.assertEqual(
            output["provenance_path"],
            "system/.ordax/native-release-tools.json",
        )
        self.assertEqual(output["final_artifact_owner"], "tools/release-bundle")
        self.assertEqual(output["final_artifact"], "system.tar")

    def test_helpers_are_prebuilt_and_fail_closed(self):
        helpers = {helper["path"]: helper for helper in CONTRACT["helpers"]}
        self.assertEqual(set(helpers), {
            "system/bin/ordax-native-install-targets",
            "system/bin/ordax-runtime-component-channel",
        })

        install = helpers["system/bin/ordax-native-install-targets"]
        self.assertEqual(install["role"], "native-install-read-only-target-discovery")
        self.assertFalse(install["physical_apply_implemented"])
        self.assertFalse(install["physical_apply_authorized"])
        self.assertFalse(install["component_publish_authorized"])

        component = helpers["system/bin/ordax-runtime-component-channel"]
        self.assertEqual(
            component["role"],
            "runtime-component-verifier-and-activation-state-owner",
        )
        self.assertFalse(component["private_signing_key_access"])
        self.assertFalse(component["component_publish_authorized"])
        self.assertFalse(component["runtime_slot_serving_authorized"])

        for helper in helpers.values():
            self.assertTrue(helper["sha256_required"])
            self.assertTrue(helper["size_required"])
            self.assertEqual(helper["mode"], "0755")

    def test_release_protocol_is_not_forked(self):
        policy = CONTRACT["release_policy"]
        self.assertFalse(policy["separate_download_channel"])
        self.assertFalse(policy["runtime_compilation_allowed"])
        self.assertFalse(policy["end_user_toolchain_required"])
        self.assertTrue(policy["covered_by_system_tar_signature"])
        self.assertTrue(policy["canonical_release_protocol_unchanged"])
        self.assertTrue(policy["component_trust_domain_remains_separate"])


if __name__ == "__main__":
    unittest.main()
