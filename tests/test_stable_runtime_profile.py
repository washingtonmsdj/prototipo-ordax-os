#!/usr/bin/env python3
"""Regress Stable/MVP runtime selection without operational Git."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "bootstrap" / "entrypoint"
DEV_RUN = ROOT / "bootstrap" / "dev-base" / "ordax-run"
ENTRYPOINT = ROOT / "system" / "entrypoint"
SUPERVISOR = ROOT / "system" / "supervisor"
SURFACE = ROOT / "system" / "surface" / "bin" / "ordax-surface"
BASE_OWNER = ROOT / "system" / "services" / "base-update" / "agent.sh"
TELEMETRY = ROOT / "system" / "services" / "telemetry" / "base-agent.sh"
CONTRACT = json.loads(
    (ROOT / "docs/contracts/distribution-profiles.json").read_text(encoding="utf-8")
)


class StableRuntimeProfileTests(unittest.TestCase):
    def test_shell_boundaries_remain_syntax_valid(self):
        for path in (
            BOOTSTRAP,
            DEV_RUN,
            ENTRYPOINT,
            SUPERVISOR,
            SURFACE,
            BASE_OWNER,
            TELEMETRY,
        ):
            subprocess.run(["sh", "-n", str(path)], check=True)

    def test_canonical_bootstrap_binds_verified_release_identity_to_stable(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("current_release_sha()", text)
        self.assertIn("[ -L /ordax/current ]", text)
        self.assertIn('case "$target" in', text)
        self.assertIn("releases/*)", text)
        self.assertIn("ORDAX_DISTRIBUTION_PROFILE=stable-mvp", text)
        self.assertIn('ORDAX_SOURCE_SHA="$source_sha"', text)
        self.assertIn('boot_current || recovery "verified release handoff failed"', text)

    def test_owner_handoff_binds_git_head_to_owner_profile(self):
        text = DEV_RUN.read_text(encoding="utf-8")
        self.assertIn('"$GIT_BIN" -C "$WORKTREE" rev-parse HEAD', text)
        self.assertIn("ORDAX_DISTRIBUTION_PROFILE=owner-development", text)
        self.assertIn('ORDAX_SOURCE_SHA="$source_sha"', text)

    def test_guardian_uses_explicit_sha_for_stable_health(self):
        text = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn('DISTRIBUTION_PROFILE=${ORDAX_DISTRIBUTION_PROFILE:-owner-development}', text)
        self.assertIn('SOURCE_SHA_HINT=${ORDAX_SOURCE_SHA:-}', text)
        resolver = text.split("runtime_source_sha() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("stable-mvp)", resolver)
        self.assertIn("SOURCE_SHA_HINT", resolver)
        self.assertIn("owner-development)", resolver)
        heartbeat = text.split("write_base_update_heartbeat() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("runtime_source_sha", heartbeat)
        self.assertNotIn("rev-parse HEAD", heartbeat)

    def test_stable_supervisor_stages_signed_release_before_owner_git_path(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn('DISTRIBUTION_PROFILE=${ORDAX_DISTRIBUTION_PROFILE:-owner-development}', text)
        current = text.split("current_sha() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("stable-mvp)", current)
        self.assertIn("SOURCE_SHA_HINT", current)

        check = text.split("check_for_update() {", 1)[1].split("\n}", 1)[0]
        stable_guard = '[ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]'
        self.assertIn(stable_guard, check)
        self.assertIn('check_stable_signed_update "$current"', check)
        self.assertLess(check.index(stable_guard), check.index("ls-remote"))

        channel = text.split("stable_channel_url() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('[ ! -L "$STABLE_CHANNEL_FILE" ]', channel)
        self.assertIn("https://*", channel)
        stable_stage = text.split("check_stable_signed_update() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('[ -L "$STABLE_RELEASE_AGENT" ]', stable_stage)
        self.assertIn('[ -L "$STABLE_TRUST_FILE" ]', stable_stage)
        self.assertIn('"$STABLE_RELEASE_AGENT" inspect', stable_stage)
        self.assertIn('"$STABLE_RELEASE_AGENT" materialize', stable_stage)
        self.assertIn('--expected-commit "$remote_sha"', stable_stage)
        self.assertIn('write_state_value "$STAGED_RELEASE_FILE" "$remote_sha"', stable_stage)
        self.assertIn("stable_release_tree_is_valid", stable_stage)
        self.assertNotIn(" install ", stable_stage)
        self.assertNotIn("activate", stable_stage.lower())
        self.assertNotIn("/ordax/current", stable_stage)
        self.assertNotIn("ls-remote", stable_stage)
        self.assertNotIn("fetch --no-tags", stable_stage)

        rollback = text.split("rollback_boot_candidate() {", 1)[1].split("\n}", 1)[0]
        self.assertIn(
            '[ "$DISTRIBUTION_PROFILE" = "owner-development" ] || return 1',
            rollback,
        )
        start = text.split("start_surface() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('start_surface_from_system "$SYSTEM_ROOT" "$(current_sha)"', start)
        shared_start = text.split("start_surface_from_system() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('ORDAX_DISTRIBUTION_PROFILE="$DISTRIBUTION_PROFILE"', shared_start)
        self.assertIn('ORDAX_SOURCE_SHA="$surface_source_sha"', shared_start)
        self.assertIn(
            'if [ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]; then\n    rm -f "$SUPERVISOR_GUARD_FILE"',
            text,
        )

    def test_surface_uses_release_sha_and_disables_dev_rescue_in_stable(self):
        text = SURFACE.read_text(encoding="utf-8")
        configure = text.split("configure_graphics_host() {", 1)[1].split("\n}", 1)[0]
        self.assertIn("stable-mvp)", configure)
        self.assertIn("SOURCE_SHA=$SOURCE_SHA_HINT", configure)
        self.assertIn("owner-development)", configure)

        rescue = text.split("ensure_rescue_agent() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('[ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]', rescue)
        self.assertIn("development Git rescue is disabled in Stable/MVP", rescue)

        owner = text.split("ensure_base_update_agent() {", 1)[1].split("\n}", 1)[0]
        self.assertIn('[ "$DISTRIBUTION_PROFILE" = "owner-development" ]', owner)
        self.assertIn('[ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]', owner)
        self.assertIn(
            "Base update owner is disabled in Stable/MVP until signed update integration is connected",
            owner,
        )
        self.assertIn('ORDAX_BASE_SOURCE_SHA="$SOURCE_SHA"', owner)

    def test_stable_base_owner_does_not_run_development_candidate_pipeline(self):
        text = BASE_OWNER.read_text(encoding="utf-8")
        loop = text.rsplit("while :; do", 1)[1]
        self.assertIn('case "$DISTRIBUTION_PROFILE" in', loop)
        self.assertIn("stable-mvp)", loop)
        self.assertIn("source_sha=$SOURCE_SHA_HINT", loop)
        self.assertIn('if [ "$DISTRIBUTION_PROFILE" = "owner-development" ]; then', loop)
        owner_only = loop.split(
            'if [ "$DISTRIBUTION_PROFILE" = "owner-development" ]; then',
            1,
        )[1].split("\n        fi", 1)[0]
        for call in (
            "prepare_dev_base_candidate",
            "prepare_esp_readonly_preflight",
            "prepare_dev_base_physical_stage",
            "prepare_dev_base_activation_readiness",
            "prepare_dev_base_postboot_promotion",
        ):
            self.assertIn(call, owner_only)

    def test_telemetry_uses_explicit_stable_sha(self):
        text = TELEMETRY.read_text(encoding="utf-8")
        self.assertIn('SOURCE_SHA_HINT=${ORDAX_SOURCE_SHA:-}', text)
        source = text.split('source_sha=""', 1)[1].split("update_status=", 1)[0]
        self.assertIn("stable-mvp)", source)
        self.assertIn("source_sha=$SOURCE_SHA_HINT", source)
        self.assertIn("owner-development)", source)
        self.assertIn("rev-parse HEAD", source)

    def test_contract_marks_signed_polling_and_materialization_without_activation(self):
        stable = CONTRACT["profiles"]["stable-mvp"]
        self.assertTrue(stable["runtime_profile_selection_implemented"])
        self.assertFalse(stable["git_update_polling_enabled"])
        self.assertFalse(stable["development_git_rescue_enabled"])
        self.assertFalse(stable["development_base_channel_enabled"])
        self.assertFalse(stable["continuous_signed_runtime_update_connected"])
        self.assertFalse(stable["base_update_owner_active"])
        self.assertEqual(
            stable["base_update_owner_activation_gate"],
            "stable-continuous-signed-update",
        )
        self.assertTrue(stable["signed_release_discovery_implemented"])
        self.assertTrue(stable["signed_release_discovery_source_implemented"])
        self.assertFalse(stable["signed_release_discovery_physical_agent_ready"])
        self.assertTrue(stable["signed_release_discovery_asset_published"])
        self.assertTrue(stable["signed_release_seed_media_includes_inspect"])
        self.assertFalse(stable["signed_release_discovery_downloads_artifact"])
        self.assertFalse(stable["signed_release_discovery_changes_current"])
        self.assertTrue(stable["periodic_signed_channel_polling_connected"])
        self.assertEqual(stable["periodic_signed_channel_default_seconds"], 60)
        self.assertTrue(stable["signed_release_materialization_connected"])
        self.assertTrue(stable["signed_release_materialization_exact_commit_required"])
        self.assertFalse(stable["signed_release_staging_changes_current"])
        self.assertFalse(stable["signed_release_staging_activation_performed"])
        self.assertFalse(stable["signed_release_activation_connected"])
        self.assertFalse(stable["continuous_signed_runtime_update_connected"])
        self.assertTrue(stable["staged_release_health_connected"])
        self.assertTrue(stable["staged_release_health_requires_candidate_sha_match"])
        self.assertTrue(stable["staged_release_health_requires_process_survival"])
        self.assertTrue(stable["staged_release_health_requires_heartbeat"])
        self.assertTrue(stable["staged_release_health_requires_known_good_restore"])
        self.assertFalse(stable["staged_release_health_changes_current"])
        self.assertFalse(stable["staged_release_health_activation_performed"])
        self.assertEqual(
            CONTRACT["next_gate"]["id"],
            "stable-exact-release-activation",
        )


if __name__ == "__main__":
    unittest.main()
