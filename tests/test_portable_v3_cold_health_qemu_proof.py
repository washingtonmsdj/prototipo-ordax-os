import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "bootstrap" / "portable-v2" / "qemu_cold_health_commit.py"
BASE_RUNNER = ROOT / "bootstrap" / "portable-v2" / "qemu_boot.py"
SUPERVISOR = ROOT / "system" / "supervisor"
WORKFLOW = ROOT / ".github" / "workflows" / "portable-v2-qemu-boot-proof.yml"
SPEC = ROOT / "docs" / "contracts" / "portable-v3-cold-health-qemu-proof-spec.json"


class PortableV3ColdHealthQemuProofTests(unittest.TestCase):
    def test_supervisor_marker_is_emitted_only_after_real_commit_path(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        handler = text.split("handle_portable_candidate_boot() {", 1)[1].split("\n}", 1)[0]
        commit = handler.index('portable_commit_candidate "$candidate_sha"')
        applied = handler.index('record_applied "$candidate_sha" signed-release')
        marker = handler.index('ORDAX_PORTABLE_COLD_HEALTH_COMMIT=$candidate_sha')
        health = handler.index(
            'wait_for_surface_health "$candidate_sha" "$INITIAL_SURFACE_HEALTH_TIMEOUT"'
        )
        self.assertLess(health, commit)
        self.assertLess(commit, applied)
        self.assertLess(applied, marker)
        self.assertIn('>/dev/console', handler)

    def test_base_qemu_runner_can_wait_for_post_health_observation(self):
        text = BASE_RUNNER.read_text(encoding="utf-8")
        self.assertIn("required_post_marker: str | None = None", text)
        self.assertIn("required_post_marker in text", text)
        self.assertIn('"required_post_marker_seen"', text)
        self.assertIn('"-net", "none"', text)
        self.assertIn("cache=directsync", text)

    def test_cold_health_runner_uses_real_supervisor_commit_and_second_boot(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("ORDAX_PORTABLE_COLD_HEALTH_COMMIT=", text)
        self.assertIn('expected_slot="candidate"', text)
        self.assertIn('expected_slot="current"', text)
        self.assertIn("required_post_marker=commit_marker", text)
        self.assertIn('"current_promoted_to_candidate"', text)
        self.assertIn('"known_good_rotated_to_previous"', text)
        self.assertIn('"candidate_file_removed"', text)
        self.assertIn('"activation_transaction_removed"', text)
        self.assertIn('"cold_health_commit_proven": True', text)
        self.assertIn('"physical_target_device_touched": False', text)
        self.assertIn('"physical_write_authorized": False', text)
        self.assertIn('"physical_usb_boot_proven": False', text)
        self.assertIn('"secure_boot_proven": False', text)

    def test_final_state_is_inspected_read_only(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"mount.exfat-fuse", "-o", "ro"', text)
        self.assertIn('"loop,ro,noload"', text)
        self.assertIn("shutil.copyfile(state_image, state_copy)", text)
        self.assertIn("current == candidate_commit", text)
        self.assertIn("known_good == previous_commit", text)
        self.assertIn("rejected != candidate_commit", text)

    def test_contract_does_not_promote_ci_to_physical_evidence(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["$schema"],
            "prototype-ordax.portable-v3-cold-health-qemu-proof-spec/1",
        )
        self.assertEqual(
            spec["proof_mode"],
            "armed-candidate-real-supervisor-cold-health-commit",
        )
        self.assertEqual(spec["required_final_state"]["current"], "candidate")
        self.assertEqual(spec["required_final_state"]["known_good"], "previous")
        self.assertEqual(spec["required_final_state"]["second_boot_slot"], "current")
        self.assertTrue(spec["safety"]["post_commit_marker_is_observation_only"])
        self.assertTrue(
            spec["safety"]["marker_emitted_only_after_real_portable_state_commit"]
        )
        self.assertFalse(spec["safety"]["physical_target_device_touched"])
        self.assertFalse(spec["safety"]["physical_write_authorized"])
        self.assertFalse(spec["safety"]["physical_usb_boot_proven"])
        self.assertFalse(spec["safety"]["secure_boot_proven"])
        self.assertFalse(spec["promotion_effect"]["physical_cold_health_gate_closed"])
        self.assertFalse(spec["promotion_effect"]["physical_known_good_gate_closed"])
        self.assertFalse(spec["promotion_effect"]["physical_rollback_gate_closed"])

    def test_workflow_exercises_both_failure_and_healthy_paths(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("PORTABLE_V4_TO_V3_QEMU_ONE_SHOT_FALLBACK=PASS", text)
        self.assertIn("qemu_cold_health_commit.py", text)
        self.assertIn("PORTABLE_V4_QEMU_COLD_HEALTH_COMMIT=PASS", text)
        self.assertIn("qemu-cold-health-proof/proof.json", text)


if __name__ == "__main__":
    unittest.main()
