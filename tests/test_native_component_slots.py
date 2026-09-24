#!/usr/bin/env python3
"""Regression tests for the fail-closed Native component-slot reader."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "system" / "surface" / "runtime" / "native_component_slots.py"

spec = importlib.util.spec_from_file_location("ordax_native_component_slots_test", MODULE)
slots = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = slots
spec.loader.exec_module(slots)


class NativeComponentSlotTests(unittest.TestCase):
    def make_capability_files(self, root: Path) -> tuple[Path, Path]:
        helper = root / "ordax-runtime-component-channel"
        helper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        helper.chmod(0o755)
        trust = root / "runtime-components-ed25519.json"
        trust.write_text("{}\n", encoding="utf-8")
        trust.chmod(0o644)
        return helper, trust

    def test_reader_requires_stable_usb_and_real_helper_and_trust(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper, trust = self.make_capability_files(root)

            self.assertTrue(
                slots.component_slot_reader_available(
                    helper_path=str(helper),
                    trust_path=str(trust),
                    distribution_profile="stable-mvp",
                    product_mode="usb",
                )
            )
            self.assertFalse(
                slots.component_slot_reader_available(
                    helper_path=str(helper),
                    trust_path=str(trust),
                    distribution_profile="owner-development",
                    product_mode="usb",
                )
            )
            self.assertFalse(
                slots.component_slot_reader_available(
                    helper_path=str(helper),
                    trust_path=str(trust),
                    distribution_profile="stable-mvp",
                    product_mode="native-disk",
                )
            )

            helper.unlink()
            helper.symlink_to("/bin/true")
            self.assertFalse(
                slots.component_slot_reader_available(
                    helper_path=str(helper),
                    trust_path=str(trust),
                    distribution_profile="stable-mvp",
                    product_mode="usb",
                )
            )

    def test_current_bundled_resolution_is_parsed_without_slot_claim(self):
        output = (
            b"RUNTIME_COMPONENT_CURRENT_RESOLVED=YES\n"
            b"COMPONENT_ID=internet\n"
            b"REVISION=0\n"
            b"SOURCE=BUNDLED\n"
            b"RUNTIME_SERVED_FROM_SLOT=NO\n"
        )
        completed = subprocess.CompletedProcess([], 0, stdout=output, stderr=b"")
        with mock.patch.object(slots.subprocess, "run", return_value=completed) as run:
            resolution = slots.resolve_component_slot(
                helper_path="/signed/bin/ordax-runtime-component-channel",
                trust_path="/signed/trust/runtime-components-ed25519.json",
                component_id="internet",
                state="current",
            )
        self.assertEqual(resolution.source, "bundled")
        self.assertIsNone(resolution.entrypoint)
        self.assertIsNone(resolution.slot)
        argv = run.call_args.args[0]
        self.assertEqual(argv[1], "resolve-current")
        self.assertIn("--trust", argv)
        self.assertIn("--root", argv)

    def test_pending_resolution_is_exact_and_keeps_probation_health(self):
        commit = "7" * 40
        output = (
            "RUNTIME_COMPONENT_PENDING_RESOLVED=YES\n"
            "COMPONENT_ID=internet\n"
            "REVISION=3\n"
            "SOURCE=SLOT\n"
            "PENDING_VERSION=0.4.0\n"
            f"PENDING_SOURCE_COMMIT={commit}\n"
            "PENDING_HEALTH=unknown\n"
            "/var/lib/ordax/components/internet/versions/0.4.0/"
            f"{commit}"
        )
        # Insert the keyed slot field before the final entrypoint fields.
        slot_path = f"/var/lib/ordax/components/internet/versions/0.4.0/{commit}"
        output = (
            "RUNTIME_COMPONENT_PENDING_RESOLVED=YES\n"
            "COMPONENT_ID=internet\n"
            "REVISION=3\n"
            "SOURCE=SLOT\n"
            "PENDING_VERSION=0.4.0\n"
            f"PENDING_SOURCE_COMMIT={commit}\n"
            "PENDING_HEALTH=unknown\n"
            f"SLOT={slot_path}\n"
            "ENTRYPOINT=system/apps/internet/runtime.mjs\n"
            "RUNTIME_SERVED_FROM_SLOT=NO\n"
        ).encode("utf-8")
        completed = subprocess.CompletedProcess([], 0, stdout=output, stderr=b"")
        with mock.patch.object(slots.subprocess, "run", return_value=completed):
            resolution = slots.resolve_component_slot(
                helper_path="/signed/bin/ordax-runtime-component-channel",
                trust_path="/signed/trust/runtime-components-ed25519.json",
                component_id="internet",
                state="pending",
            )
        self.assertEqual(resolution.source, "slot")
        self.assertEqual(resolution.version, "0.4.0")
        self.assertEqual(resolution.source_commit, commit)
        self.assertEqual(resolution.pending_health, "unknown")
        self.assertEqual(resolution.entrypoint, "system/apps/internet/runtime.mjs")
        self.assertEqual(resolution.slot, slot_path)

    def test_runtime_file_read_uses_fixed_argv_and_returns_only_verified_stdout(self):
        payload = b'export const componentRuntime = { schema: "ordax.component-runtime/1" };\n'
        completed = subprocess.CompletedProcess([], 0, stdout=payload, stderr=b"")
        with mock.patch.object(slots.subprocess, "run", return_value=completed) as run:
            result = slots.read_component_runtime_file(
                helper_path="/signed/bin/ordax-runtime-component-channel",
                trust_path="/signed/trust/runtime-components-ed25519.json",
                component_id="internet",
                state="pending",
                version="0.4.0",
                source_commit="7777777777777777777777777777777777777777",
                requested_path="system/apps/internet/runtime.mjs",
            )
        self.assertEqual(result, payload)
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "/signed/bin/ordax-runtime-component-channel")
        self.assertEqual(argv[1], "read-runtime-file")
        self.assertIn("--version", argv)
        self.assertIn("0.4.0", argv)
        self.assertIn("--source-commit", argv)
        self.assertIn("7777777777777777777777777777777777777777", argv)
        self.assertIn("system/apps/internet/runtime.mjs", argv)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.PIPE)

    def test_invalid_component_and_paths_fail_before_verifier_execution(self):
        with mock.patch.object(slots.subprocess, "run") as run:
            with self.assertRaises(slots.ComponentSlotRequestError):
                slots.read_component_runtime_file(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="notes",
                    state="pending",
                    version="0.4.0",
                    source_commit="7777777777777777777777777777777777777777",
                    requested_path="system/apps/notes/runtime.mjs",
                )
            with self.assertRaises(slots.ComponentSlotRequestError):
                slots.read_component_runtime_file(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="internet",
                    state="pending",
                    version="0.4.0",
                    source_commit="7777777777777777777777777777777777777777",
                    requested_path="../escape.mjs",
                )
        run.assert_not_called()

    def test_runtime_file_read_rejects_invalid_slot_identity_before_verifier(self):
        with mock.patch.object(slots.subprocess, "run") as run:
            with self.assertRaises(slots.ComponentSlotRequestError):
                slots.read_component_runtime_file(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="internet",
                    state="pending",
                    version="not-semver",
                    source_commit="7" * 40,
                    requested_path="system/apps/internet/runtime.mjs",
                )
            with self.assertRaises(slots.ComponentSlotRequestError):
                slots.read_component_runtime_file(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="internet",
                    state="pending",
                    version="0.4.0",
                    source_commit="bad-sha",
                    requested_path="system/apps/internet/runtime.mjs",
                )
        run.assert_not_called()

    def test_verifier_rejection_and_timeout_fail_closed(self):
        rejected = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"rejected")
        with mock.patch.object(slots.subprocess, "run", return_value=rejected):
            with self.assertRaises(slots.ComponentSlotVerificationError):
                slots.resolve_component_slot(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="internet",
                    state="pending",
                )

        with mock.patch.object(
            slots.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["helper"], timeout=3),
        ):
            with self.assertRaises(slots.ComponentSlotUnavailableError):
                slots.resolve_component_slot(
                    helper_path="/signed/bin/helper",
                    trust_path="/signed/trust.json",
                    component_id="internet",
                    state="pending",
                )


if __name__ == "__main__":
    unittest.main()
