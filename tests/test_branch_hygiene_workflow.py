#!/usr/bin/env python3
"""Regress the automatic branch-hygiene safety boundary."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "branch-hygiene.yml"


class BranchHygieneWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_main_push_always_runs_general_prune(self):
        trigger = self.text.split("on:", 1)[1].split("permissions:", 1)[0]
        self.assertIn("push:\n    branches:\n      - main", trigger)
        self.assertNotIn("paths:", trigger)
        self.assertIn(
            "if: github.event_name == 'workflow_dispatch' || github.event_name == 'push'",
            self.text,
        )

    def test_protected_and_open_pr_heads_are_preserved(self):
        self.assertIn('case "$HEAD_REF" in\n            main|ordax-rescue)', self.text)
        self.assertIn(
            'preserve = {"main", "ordax-rescue"} | open_heads',
            self.text,
        )

    def test_merged_head_is_deleted_only_if_unchanged(self):
        self.assertIn('if [[ "$current_sha" != "$MERGED_HEAD_SHA" ]]', self.text)
        self.assertIn(
            'echo "Preserving $HEAD_REF because it changed after the merged PR."',
            self.text,
        )

    def test_closed_unmerged_prune_requires_exact_closed_head_and_no_open_pr(self):
        self.assertIn("latest_closed_unmerged = {}", self.text)
        self.assertIn('if pr.get("merged_at") or not head_repo:', self.text)
        self.assertIn(
            'preserve = {"main", "ordax-rescue"} | open_heads',
            self.text,
        )
        self.assertIn('if current_sha != closed_head_sha:', self.text)
        self.assertIn("changed_after_close.append(ref)", self.text)
        self.assertIn("Deleted closed-unmerged branch: $ref", self.text)

    def test_general_prune_deletes_only_fully_contained_heads(self):
        self.assertIn('if int(compare.get("ahead_by", 1)) == 0:', self.text)
        self.assertIn("candidates.append(ref)", self.text)


if __name__ == "__main__":
    unittest.main()
