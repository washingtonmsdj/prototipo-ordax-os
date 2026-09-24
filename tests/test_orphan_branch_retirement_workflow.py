#!/usr/bin/env python3
"""Regress the one-shot orphan branch retirement safety boundary."""

from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "retire-orphan-branches.yml"
CONTRACT = ROOT / "docs" / "evidence" / "branch-retirement-20260924.json"


class OrphanBranchRetirementWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_bounded_and_exact(self):
        branches = self.contract["branches"]
        self.assertEqual(self.contract["audit"]["orphan_branch_count"], 23)
        self.assertEqual(len(branches), 23)
        self.assertEqual(len({item["branch"] for item in branches}), 23)
        for item in branches:
            self.assertRegex(item["expected_head_sha"], r"^[0-9a-f]{40}$")
            self.assertEqual(
                item["archive_tag"],
                "archive/branches/20260924/" + item["branch"],
            )

    def test_active_and_protected_heads_fail_closed(self):
        self.assertIn('preserve = {"main", "ordax-rescue"} | open_heads', self.workflow)
        self.assertIn("branch is protected or now used by an open PR", self.workflow)

    def test_current_head_must_match_contract_before_retirement(self):
        self.assertIn("current != expected", self.workflow)
        self.assertIn("RETIREMENT_PRECHECK=FAIL", self.workflow)
        self.assertIn("RETIREMENT_PRECHECK=PASS", self.workflow)

    def test_archive_tag_is_verified_before_branch_delete(self):
        verify_index = self.workflow.index("archive tag verification failed")
        delete_index = self.workflow.index('"--method", "DELETE"')
        self.assertLess(verify_index, delete_index)
        self.assertIn("refs/tags/", self.workflow)
        self.assertIn("ARCHIVED_AND_DELETED", self.workflow)


if __name__ == "__main__":
    unittest.main()
