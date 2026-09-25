import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "public-identity" / "supabase_account.py"

spec = importlib.util.spec_from_file_location("ordax_supabase_account", MODULE)
account_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = account_module
spec.loader.exec_module(account_module)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        status, value = self.responses.pop(0)
        return status, json.dumps(value).encode("utf-8")


def valid_export():
    return {
        "$schema": "prototype-ordax.account-export/1",
        "subject": "00000000-0000-0000-0000-000000000001",
        "exported_at": "2026-09-25T00:00:00Z",
        "account": {},
        "spaces": [],
        "memberships": [],
        "space_profile_packs": [],
        "entitlements": [],
        "projects": [],
        "devices": [],
        "project_connections": [],
        "memory_items": [],
        "sync_objects": [],
    }


class SupabaseAccountProviderTests(unittest.TestCase):
    def provider(self, responses):
        transport = FakeTransport(responses)
        provider = account_module.SupabaseAccountProvider(
            "https://ordax-example.supabase.co",
            "sb_publishable_1234567890",
            transport=transport,
        )
        return provider, transport

    def test_rejects_secret_or_non_https_configuration(self):
        with self.assertRaises(ValueError):
            account_module.SupabaseAccountProvider(
                "http://ordax-example.supabase.co",
                "sb_publishable_1234567890",
            )
        for key in ("sb_secret_1234567890", "service_role", "legacy-anon-key"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    account_module.SupabaseAccountProvider(
                        "https://ordax-example.supabase.co",
                        key,
                    )

    def test_export_calls_rls_scoped_rpc_with_user_bearer_token(self):
        provider, transport = self.provider([(200, valid_export())])
        result = provider.export_account("user-access-token")
        self.assertEqual(result["$schema"], "prototype-ordax.account-export/1")
        method, url, headers, body = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/rest/v1/rpc/ordax_account_export_v1"))
        self.assertEqual(headers["Authorization"], "Bearer user-access-token")
        self.assertEqual(headers["apikey"], "sb_publishable_1234567890")
        self.assertEqual(body, b"{}")

    def test_export_rejects_invalid_schema_or_sections(self):
        invalid = valid_export()
        invalid["sync_objects"] = {}
        provider, _ = self.provider([(200, invalid)])
        with self.assertRaises(account_module.SupabaseAccountError):
            provider.export_account("user-access-token")

    def test_provider_error_does_not_echo_bearer_token(self):
        provider, _ = self.provider([(500, {"message": "failure"})])
        with self.assertRaises(account_module.SupabaseAccountError) as caught:
            provider.export_account("TOP-SECRET-TOKEN")
        self.assertNotIn("TOP-SECRET-TOKEN", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
