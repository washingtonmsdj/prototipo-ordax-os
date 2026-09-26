import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "system" / "entrypoint"
SUPERVISOR = ROOT / "system" / "supervisor"


class StableInitialSurfaceHealthBudgetTests(unittest.TestCase):
    def test_stable_guardian_sets_bounded_cold_start_budget_without_overriding_operator(self):
        entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
        stable_block = entrypoint.split('if [ "$DISTRIBUTION_PROFILE" = "stable-mvp" ]; then', 1)[1].split("\nfi", 1)[0]

        self.assertIn(
            'if [ -z "${ORDAX_INITIAL_SURFACE_HEALTH_TIMEOUT_SECONDS+x}" ]; then',
            stable_block,
        )
        self.assertIn("ORDAX_INITIAL_SURFACE_HEALTH_TIMEOUT_SECONDS=60", stable_block)
        self.assertIn("export ORDAX_INITIAL_SURFACE_HEALTH_TIMEOUT_SECONDS", stable_block)
        self.assertNotIn("ORDAX_INITIAL_SURFACE_HEALTH_TIMEOUT_SECONDS=180", stable_block)

    def test_supervisor_remains_configurable_and_cold_candidate_uses_initial_budget(self):
        supervisor = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn(
            'INITIAL_SURFACE_HEALTH_TIMEOUT=${ORDAX_INITIAL_SURFACE_HEALTH_TIMEOUT_SECONDS:-30}',
            supervisor,
        )
        self.assertIn(
            'wait_for_surface_health "$candidate_sha" "$INITIAL_SURFACE_HEALTH_TIMEOUT"',
            supervisor,
        )
        self.assertIn(
            '[ "$INITIAL_SURFACE_HEALTH_TIMEOUT" -ge 15 ] 2>/dev/null || INITIAL_SURFACE_HEALTH_TIMEOUT=30',
            supervisor,
        )


if __name__ == "__main__":
    unittest.main()
