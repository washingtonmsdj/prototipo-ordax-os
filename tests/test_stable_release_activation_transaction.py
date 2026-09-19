#!/usr/bin/env python3
"""Regress the crash-safe Stable/MVP exact activation transaction."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "system" / "entrypoint"
SUPERVISOR = ROOT / "system" / "supervisor"


def function_body(text: str, name: str) -> str:
    marker = f"{name}() {{"
    return text.split(marker, 1)[1].split("\n}", 1)[0]


class StableReleaseActivationTransactionTests(unittest.TestCase):
    def test_shell_boundaries_are_valid(self):
        subprocess.run(["sh", "-n", str(ENTRYPOINT)], check=True)
        subprocess.run(["sh", "-n", str(SUPERVISOR)], check=True)

    def test_guardian_derives_stable_identity_from_current_symlink(self):
        text = ENTRYPOINT.read_text(encoding="utf-8")
        resolver = function_body(text, "stable_current_release_sha")
        self.assertIn("current=$STABLE_ROOT/current", resolver)
        self.assertIn('[ -L "$current" ]', resolver)
        self.assertIn('releases/*)', resolver)
        self.assertIn('[ -x "$STABLE_ROOT/releases/$value/system/entrypoint" ]', resolver)

        runtime = function_body(text, "runtime_source_sha")
        self.assertIn("stable_current_release_sha", runtime)

        refresh = text.split('if [ "$supervisor_rc" -eq 75 ]; then', 1)[1].split(
            "\n    fi",
            1,
        )[0]
        self.assertIn("stable_current_release_sha", refresh)
        self.assertIn("ORDAX_SOURCE_SHA=$SOURCE_SHA_HINT", refresh)
        self.assertIn("SYSTEM_ROOT=$STABLE_ROOT/current/system", refresh)
        self.assertIn('exec "$SYSTEM_ENTRYPOINT"', refresh)

    def test_stable_current_sha_tracks_symlink_not_inherited_hint(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        resolver = function_body(text, "stable_current_release_sha")
        self.assertIn("current=$STABLE_ROOT/current", resolver)
        current = function_body(text, "current_sha")
        self.assertIn("stable_current_release_sha", current)
        stable_case = current.split("stable-mvp)", 1)[1].split(";;", 1)[0]
        self.assertNotIn("SOURCE_SHA_HINT", stable_case)

    def test_guard_is_persisted_before_exact_activation(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        guard = function_body(text, "write_stable_activation_guard")
        self.assertIn('printf \'%s %s %s', guard)
        self.assertIn('mv -f "$temporary" "$STABLE_ACTIVATION_GUARD_FILE"', guard)
        self.assertIn("/bin/busybox sync", guard)

        activate = function_body(text, "activate_health_ready_stable_release")
        staged = 'staged_sha=$(read_state_value "$STAGED_RELEASE_FILE")'
        ready = 'ready_sha=$(read_state_value "$STABLE_HEALTH_READY_FILE")'
        staged_match = '[ "$staged_sha" = "$candidate_sha" ]'
        ready_match = '[ "$ready_sha" = "$candidate_sha" ]'
        write_guard = 'write_stable_activation_guard "$previous_sha" "$candidate_sha" "$attempt_id"'
        swap = 'stable_activate_exact_to "$candidate_sha" "$STABLE_ACTIVATION_RECEIPT"'
        for needle in (staged, ready, staged_match, ready_match, write_guard, swap):
            self.assertIn(needle, activate)
        self.assertLess(activate.index(staged_match), activate.index(write_guard))
        self.assertLess(activate.index(ready_match), activate.index(write_guard))
        self.assertLess(activate.index(write_guard), activate.index(swap))

    def test_exact_activation_helper_has_no_network_or_git(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        helper = function_body(text, "stable_activate_exact_to")
        self.assertIn('"$STABLE_RELEASE_AGENT" activate-exact', helper)
        self.assertIn('--trust "$STABLE_TRUST_FILE"', helper)
        self.assertIn('--root "$STABLE_ROOT"', helper)
        self.assertIn('--expected-commit "$expected_sha"', helper)
        self.assertNotIn("--envelope-url", helper)
        self.assertNotIn("ls-remote", helper)
        self.assertNotIn("fetch ", helper)
        self.assertNotIn("git ", helper.lower())

    def test_ambiguous_activation_is_recovered_by_guard(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        activate = function_body(text, "activate_health_ready_stable_release")
        self.assertIn('active_sha=$(stable_current_release_sha', activate)
        self.assertIn('[ "$active_sha" = "$previous_sha" ]', activate)
        self.assertIn('[ "$active_sha" != "$candidate_sha" ]', activate)
        self.assertIn(
            "transaction guard will arbitrate cold health",
            activate,
        )
        self.assertIn("exit 75", activate)

    def test_cold_health_commits_candidate_only_after_exact_sha_handshake(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        handler = function_body(text, "handle_stable_activation_guard")
        self.assertIn('[ "$initial_sha_value" = "$guard_candidate" ]', handler)
        self.assertIn("surface_stays_running 4", handler)
        self.assertIn(
            'wait_for_surface_health "$guard_candidate" "$SURFACE_HEALTH_TIMEOUT"',
            handler,
        )
        self.assertIn('record_applied "$guard_candidate" signed-release', handler)
        self.assertIn('record_runtime_surface_sha "$guard_candidate"', handler)
        self.assertIn('"$STABLE_ACTIVATION_GUARD_FILE"', handler)
        wait = handler.index(
            'wait_for_surface_health "$guard_candidate" "$SURFACE_HEALTH_TIMEOUT"'
        )
        committed = handler.index('record_applied "$guard_candidate" signed-release')
        self.assertLess(wait, committed)

    def test_failed_cold_health_uses_exact_offline_rollback(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        rollback = function_body(text, "rollback_stable_activation")
        self.assertIn(
            'stable_activate_exact_to "$previous_sha" "$STABLE_ROLLBACK_RECEIPT"',
            rollback,
        )
        self.assertIn(
            '[ "$rollback_sha" != "$previous_sha" ]',
            rollback,
        )
        self.assertIn(
            '[ "$rollback_previous" != "$failed_sha" ]',
            rollback,
        )
        self.assertIn(
            'write_state_value "$STABLE_HEALTH_REJECTED_FILE" "$failed_sha"',
            rollback,
        )
        self.assertIn('rm -f "$STABLE_HEALTH_READY_FILE" "$STABLE_ACTIVATION_GUARD_FILE"', rollback)
        self.assertIn("exit 75", rollback)
        self.assertNotIn("reset --hard", rollback)
        self.assertNotIn("ls-remote", rollback)
        self.assertNotIn("--envelope-url", rollback)

    def test_stable_transaction_guard_precedes_legacy_git_guard(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        stable = (
            'if [ "$DISTRIBUTION_PROFILE" = "stable-mvp" ] && '
            '[ -s "$STABLE_ACTIVATION_GUARD_FILE" ]; then'
        )
        legacy = 'elif [ -s "$SUPERVISOR_GUARD_FILE" ]; then'
        self.assertIn(stable, text)
        self.assertIn(legacy, text)
        self.assertLess(text.index(stable), text.index(legacy))

    def test_health_ready_state_is_the_only_activation_entry(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        check = function_body(text, "check_stable_signed_update")
        self.assertIn('ready_sha=$(read_state_value "$STABLE_HEALTH_READY_FILE")', check)
        self.assertIn('[ "$ready_sha" = "$remote_sha" ]', check)
        self.assertIn(
            'activate_health_ready_stable_release "$current" "$remote_sha"',
            check,
        )
        self.assertNotIn("activate-exact", check)


if __name__ == "__main__":
    unittest.main()
