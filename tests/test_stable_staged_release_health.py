#!/usr/bin/env python3
"""Regress staged Stable release health without activating /ordax/current."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "system" / "supervisor"


def function_body(text: str, name: str) -> str:
    marker = f"{name}() {{"
    return text.split(marker, 1)[1].split("\n}", 1)[0]


class StableStagedReleaseHealthTests(unittest.TestCase):
    def test_supervisor_is_shell_valid(self):
        subprocess.run(["sh", "-n", str(SUPERVISOR)], check=True)

    def test_candidate_surface_is_launched_from_immutable_release_root(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        start = function_body(text, "start_surface_from_system")
        self.assertIn("surface_entrypoint=$surface_system_root/surface/entrypoint", start)
        self.assertIn('ORDAX_SYSTEM_ROOT="$surface_system_root"', start)
        self.assertIn('ORDAX_DISTRIBUTION_PROFILE="$DISTRIBUTION_PROFILE"', start)
        self.assertIn('ORDAX_SOURCE_SHA="$surface_source_sha"', start)
        self.assertIn('"$surface_entrypoint" &', start)

        probe = function_body(text, "probe_staged_stable_release_health")
        self.assertIn(
            'candidate_system=$STABLE_ROOT/releases/$candidate_sha/system',
            probe,
        )
        self.assertIn(
            'start_surface_from_system "$candidate_system" "$candidate_sha"',
            probe,
        )
        self.assertNotIn("/ordax/current", probe)
        self.assertNotIn("activate", probe.lower())
        self.assertNotIn(" install ", probe)

    def test_candidate_health_handshake_uses_candidate_sha(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        probe = function_body(text, "probe_staged_stable_release_health")
        state_line = 'write_update_state "$candidate_sha" testing signed-release'
        start_line = 'start_surface_from_system "$candidate_system" "$candidate_sha"'
        wait_line = 'wait_for_surface_health "$candidate_sha" "$SURFACE_HEALTH_TIMEOUT"'
        self.assertIn(state_line, probe)
        self.assertIn(start_line, probe)
        self.assertIn("surface_stays_running 4", probe)
        self.assertIn(wait_line, probe)
        self.assertLess(probe.index(state_line), probe.index(start_line))
        self.assertLess(probe.index(start_line), probe.index(wait_line))

    def test_known_good_state_is_restored_before_known_good_surface_health(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        restore = function_body(text, "restore_current_surface_after_probe")
        state_line = 'write_update_state "$current_sha_value" restoring signed-release'
        start_line = "start_surface"
        wait_line = 'wait_for_surface_health "$current_sha_value" "$SURFACE_HEALTH_TIMEOUT"'
        self.assertIn(state_line, restore)
        self.assertIn(start_line, restore)
        self.assertIn(wait_line, restore)
        self.assertIn('record_runtime_surface_sha "$current_sha_value"', restore)
        self.assertLess(restore.index(state_line), restore.index(start_line))
        self.assertLess(restore.index(start_line), restore.index(wait_line))

    def test_health_ready_is_committed_only_after_known_good_restore(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        probe = function_body(text, "probe_staged_stable_release_health")
        restore = 'restore_current_surface_after_probe "$current_sha_value" "$candidate_sha"'
        ready = 'write_state_value "$STABLE_HEALTH_READY_FILE" "$candidate_sha"'
        reject = 'write_state_value "$STABLE_HEALTH_REJECTED_FILE" "$candidate_sha"'
        self.assertIn(restore, probe)
        self.assertIn(ready, probe)
        self.assertIn(reject, probe)
        self.assertLess(probe.index(restore), probe.index(ready))
        self.assertLess(probe.index(restore), probe.index(reject))

    def test_failed_candidate_is_not_retested_until_channel_changes(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        probe = function_body(text, "probe_staged_stable_release_health")
        self.assertIn(
            'rejected_sha=$(read_state_value "$STABLE_HEALTH_REJECTED_FILE")',
            probe,
        )
        self.assertIn('[ "$rejected_sha" = "$candidate_sha" ]', probe)
        self.assertIn('"stable-release-health-rejected"', probe)

        stable = function_body(text, "check_stable_signed_update")
        self.assertIn(
            '[ "$rejected_sha" = "$remote_sha" ] || rm -f "$STABLE_HEALTH_REJECTED_FILE"',
            stable,
        )

    def test_health_probe_never_mutates_current_pointer_or_reboots(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        probe = function_body(text, "probe_staged_stable_release_health")
        restore = function_body(text, "restore_current_surface_after_probe")
        for body in (probe, restore):
            self.assertNotIn("/ordax/current", body)
            self.assertNotIn(" ln -s ", body)
            self.assertNotIn("mv -f", body)
            self.assertNotIn("reboot", body.lower())
            self.assertNotIn("poweroff", body.lower())


if __name__ == "__main__":
    unittest.main()
