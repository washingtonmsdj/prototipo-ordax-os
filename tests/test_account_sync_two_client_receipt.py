from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "account-sync" / "prove_two_clients.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ordax_two_client_proof", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


proof = load_module()


class AccountSyncTwoClientReceiptTests(unittest.TestCase):
    def test_receipt_is_sanitized_and_source_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            old_sha = os.environ.get("GITHUB_SHA")
            old_run = os.environ.get("GITHUB_RUN_ID")
            try:
                os.environ["GITHUB_SHA"] = "0123456789abcdef0123456789abcdef01234567"
                os.environ["GITHUB_RUN_ID"] = "12345"
                proof.write_receipt(
                    str(path),
                    "https://example.invalid/functions/v1/ordax-account-gateway",
                    41,
                    42,
                )
            finally:
                if old_sha is None:
                    os.environ.pop("GITHUB_SHA", None)
                else:
                    os.environ["GITHUB_SHA"] = old_sha
                if old_run is None:
                    os.environ.pop("GITHUB_RUN_ID", None)
                else:
                    os.environ["GITHUB_RUN_ID"] = old_run

            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            data["$schema"],
            "prototype-ordax.account-sync-two-client-proof/1",
        )
        self.assertEqual(data["status"], "pass")
        self.assertEqual(data["proof_scope"], "two-independent-sessions-same-account")
        self.assertEqual(data["source_commit"], "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(data["workflow_run_id"], "12345")
        self.assertEqual(data["create_cursor"], 41)
        self.assertEqual(data["delete_cursor"], 42)
        self.assertTrue(data["proof_object_tombstoned"])
        self.assertFalse(data["credentials_persisted"])
        self.assertFalse(data["account_identifier_recorded"])
        self.assertFalse(data["sensitive_auth_material_recorded"])
        serialized = json.dumps(data, sort_keys=True).lower()
        self.assertNotIn("password", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("refresh_token", serialized)

    def test_invalid_source_commit_is_not_recorded_as_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            old_sha = os.environ.get("GITHUB_SHA")
            try:
                os.environ["GITHUB_SHA"] = "not-a-commit"
                proof.write_receipt(
                    str(path),
                    "https://example.invalid/functions/v1/ordax-account-gateway",
                    7,
                    8,
                )
            finally:
                if old_sha is None:
                    os.environ.pop("GITHUB_SHA", None)
                else:
                    os.environ["GITHUB_SHA"] = old_sha
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertIsNone(data["source_commit"])


if __name__ == "__main__":
    unittest.main()
