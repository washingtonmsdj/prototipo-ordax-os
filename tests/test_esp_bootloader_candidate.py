#!/usr/bin/env python3
"""Regress pinned provenance verification for ESP bootloader candidates."""

from __future__ import annotations

import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "boot/esp/build.py"


def load_module():
    spec = spec_from_file_location("ordax_esp_build_test", MODULE)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


esp_build = load_module()


class EspBootloaderCandidateVerificationTests(unittest.TestCase):
    def bundle(self, root: Path) -> dict:
        contract = esp_build.load_contract()
        boot = contract["bootloader"]
        artifact = root / "systemd-bootx64.efi"
        artifact.write_bytes(b"MZ-fake-test-only-efi-bundle\n")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        provenance = {
            "$schema": "prototype-ordax.esp-bootloader-provenance/1",
            "status": "candidate",
            "physical_artifact_authorized": False,
            "upstream_project": "systemd",
            "upstream_version": boot["version"],
            "upstream_tag": boot["tag"],
            "upstream_tag_object_sha": boot["tag_object_sha"],
            "upstream_source_commit": boot["source_commit"],
            "upstream_tag_signature_verified": True,
            "meson_target": "systemd-boot",
            "artifact": {
                "name": artifact.name,
                "sha256": digest,
                "size": artifact.stat().st_size,
            },
        }
        prov = root / "bootloader-provenance.json"
        prov.write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (root / "SHA256SUMS").write_text(
            f"{digest}  {artifact.name}\n"
            f"{hashlib.sha256(prov.read_bytes()).hexdigest()}  {prov.name}\n",
            encoding="utf-8",
        )
        return provenance

    def rewrite(self, root: Path, provenance: dict) -> None:
        prov = root / "bootloader-provenance.json"
        prov.write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        artifact = root / "systemd-bootx64.efi"
        (root / "SHA256SUMS").write_text(
            f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n"
            f"{hashlib.sha256(prov.read_bytes()).hexdigest()}  {prov.name}\n",
            encoding="utf-8",
        )

    def test_canonical_bundle_is_bound_to_current_pinned_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provenance = self.bundle(root)

            result = esp_build.verify(root)

            self.assertEqual(result["status"], "verified")
            self.assertEqual(result["artifact_count"], 2)
            self.assertEqual(
                result["upstream_version"],
                provenance["upstream_version"],
            )
            self.assertEqual(
                result["source_commit"],
                provenance["upstream_source_commit"],
            )
            self.assertEqual(
                result["artifact_sha256"],
                provenance["artifact"]["sha256"],
            )
            self.assertFalse(result["physical_artifact_authorized"])

    def test_internally_consistent_bundle_from_other_systemd_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provenance = self.bundle(root)
            provenance["upstream_source_commit"] = "f" * 40
            self.rewrite(root, provenance)

            with self.assertRaisesRegex(
                esp_build.BuildError,
                "does not match pinned contract: upstream_source_commit",
            ):
                esp_build.verify(root)

    def test_other_systemd_version_is_rejected_even_with_rehashed_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provenance = self.bundle(root)
            provenance["upstream_version"] = "999.0"
            self.rewrite(root, provenance)

            with self.assertRaisesRegex(
                esp_build.BuildError,
                "does not match pinned contract: upstream_version",
            ):
                esp_build.verify(root)

    def test_artifact_size_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provenance = self.bundle(root)
            provenance["artifact"]["size"] += 1
            self.rewrite(root, provenance)

            with self.assertRaisesRegex(
                esp_build.BuildError,
                "disagrees with bootloader size",
            ):
                esp_build.verify(root)

    def test_unexpected_provenance_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provenance = self.bundle(root)
            provenance["untrusted_note"] = "accept-me"
            self.rewrite(root, provenance)

            with self.assertRaisesRegex(
                esp_build.BuildError,
                "provenance fields are not canonical",
            ):
                esp_build.verify(root)


if __name__ == "__main__":
    unittest.main()
