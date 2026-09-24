import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QEMU = ROOT / "bootstrap" / "portable-v2" / "qemu_boot.py"
WORKFLOW = ROOT / ".github" / "workflows" / "portable-v2-qemu-boot-proof.yml"
BASELINE = ROOT / "docs" / "contracts" / "portable-v2-qemu-boot-proof.json"
SPEC = ROOT / "docs" / "contracts" / "portable-v3-one-shot-qemu-proof-spec.json"


class PortableV3OneShotQemuProofTests(unittest.TestCase):
    def test_runner_keeps_baseline_and_adds_optional_two_boot_mode(self):
        text = QEMU.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--previous-commit")', text)
        self.assertIn('previous_commit = getattr(args, "previous_commit", None)', text)
        self.assertIn('expected_slot="candidate"', text)
        self.assertIn('expected_slot="current"', text)
        self.assertIn('"candidate_boot_count": 1', text)
        self.assertIn('"fallback_boot_count": 1', text)
        self.assertIn('"cold_health_commit_proven": False', text)
        self.assertIn('"failure_fallback_proven": True', text)
        self.assertIn('"rejected_state_proven": True', text)
        self.assertIn('"candidate_file_removed"', text)
        self.assertIn('"activation_transaction_removed"', text)
        self.assertIn('"physical_target_device_untouched": True', text)
        self.assertIn('checks["guest_disk_destroyed"] = not disk.exists()', text)
        self.assertIn('"-net", "none"', text)
        self.assertIn("cache=directsync", text)
        self.assertIn('"qemu_durable_cache_mode"', text)
        self.assertIn("ORDAX_PORTABLE_ACTIVATION_STATE_DURABLE=YES", text)
        self.assertIn("ACTIVATION_DURABLE in text", text)

    def test_final_state_is_inspected_from_a_read_only_copy(self):
        text = QEMU.read_text(encoding="utf-8")
        self.assertIn('"mount.exfat-fuse", "-o", "ro"', text)
        self.assertIn('shutil.copyfile(state_image, state_copy)', text)
        self.assertIn('"loop,ro,noload"', text)
        self.assertIn('current == previous_commit', text)
        self.assertIn('known_good == previous_commit', text)
        self.assertIn('rejected == candidate_commit', text)
        self.assertIn("final one-shot state mismatch", text)

    def test_workflow_uses_real_previous_source_and_same_ephemeral_trust(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", text)
        self.assertIn('git worktree add --detach "$previous_source" "$previous"', text)
        self.assertIn('--source-commit "$previous"', text)
        self.assertIn('--expected-commit "$previous"', text)
        self.assertIn('ordax-portable-state"', text)
        self.assertIn('prepare "$mountpoint" "$portable" "$candidate"', text)
        self.assertIn('--previous-commit "$previous"', text)
        self.assertIn("PORTABLE_V4_TO_V3_QEMU_ONE_SHOT_FALLBACK=PASS", text)
        self.assertIn("PORTABLE_V4_QEMU_COLD_HEALTH_COMMIT_PROVEN=NO", text)

        previous_build = text.index('git worktree add --detach "$previous_source" "$previous"')
        key_destroy = text.index('rm -f "$work/private.pem"')
        self.assertLess(previous_build, key_destroy)

    def test_one_shot_spec_keeps_ci_and_physical_boundaries_explicit(self):
        import json

        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["$schema"],
            "prototype-ordax.portable-v3-one-shot-qemu-proof-spec/1",
        )
        self.assertEqual(spec["status"], "candidate-proof-not-yet-promoted")
        self.assertEqual(spec["proof_mode"], "armed-candidate-one-shot-fallback")
        self.assertTrue(spec["source_identity"]["previous_source_tree_required"])
        self.assertTrue(spec["source_identity"]["same_ephemeral_ci_trust_required"])
        self.assertEqual(spec["required_final_state"]["current"], "previous")
        self.assertEqual(spec["required_final_state"]["rejected"], "candidate")
        self.assertEqual(spec["required_final_state"]["candidate_file"], "absent")
        self.assertEqual(spec["required_final_state"]["activation_transaction"], "absent")
        self.assertIn(
            "sync-inner-state-and-outer-data-filesystem-before-proof-handoff",
            spec["required_sequence"],
        )
        self.assertTrue(spec["safety"]["activation_state_outer_sync_required"])
        self.assertEqual(
            spec["safety"]["activation_state_durable_serial_marker"],
            "ORDAX_PORTABLE_ACTIVATION_STATE_DURABLE=YES",
        )
        self.assertTrue(spec["safety"]["qemu_termination_requires_durable_state_marker"])
        self.assertTrue(spec["safety"]["qemu_network"] == "disabled")
        self.assertFalse(spec["safety"]["physical_target_device_touched"])
        self.assertFalse(spec["safety"]["physical_write_authorized"])
        self.assertFalse(spec["safety"]["public_physical_promotion_allowed"])
        self.assertFalse(spec["safety"]["cold_health_commit_proven"])
        self.assertFalse(spec["safety"]["physical_usb_boot_proven"])
        self.assertFalse(spec["safety"]["secure_boot_proven"])
        self.assertFalse(spec["promotion_effect"]["cold_health_commit_gate_closed"])
        self.assertFalse(spec["promotion_effect"]["physical_known_good_gate_closed"])
        self.assertFalse(spec["promotion_effect"]["physical_rollback_gate_closed"])
    def test_baseline_contract_does_not_get_rewritten_as_one_shot_evidence(self):
        text = BASELINE.read_text(encoding="utf-8")
        self.assertIn('"activation_transaction_scope": "baseline-current-boot-only"', text)
        self.assertIn('"armed_candidate_one_shot_proven": false', text)
        self.assertIn("requires a separate disposable proof", text)


if __name__ == "__main__":
    unittest.main()
