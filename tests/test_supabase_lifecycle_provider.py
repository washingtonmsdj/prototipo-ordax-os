import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "public-identity" / "supabase_lifecycle.py"

spec = importlib.util.spec_from_file_location("ordax_supabase_lifecycle", MODULE)
lifecycle_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = lifecycle_module
spec.loader.exec_module(lifecycle_module)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        status, value = self.responses.pop(0)
        return status, json.dumps(value).encode("utf-8")


class SupabaseLifecycleProviderTests(unittest.TestCase):
    def provider(self, responses):
        transport = FakeTransport(responses)
        provider = lifecycle_module.SupabaseLifecycleProvider(
            "https://ordax-example.supabase.co",
            "sb_publishable_1234567890",
            transport=transport,
        )
        return provider, transport

    def test_rejects_secret_or_non_https_configuration(self):
        with self.assertRaises(ValueError):
            lifecycle_module.SupabaseLifecycleProvider(
                "http://ordax-example.supabase.co",
                "sb_publishable_1234567890",
            )
        for key in ("sb_secret_1234567890", "service_role", "legacy-anon-key"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    lifecycle_module.SupabaseLifecycleProvider(
                        "https://ordax-example.supabase.co",
                        key,
                    )

    def test_close_requires_explicit_confirmation_before_network(self):
        provider, transport = self.provider([])
        with self.assertRaises(ValueError):
            provider.close_account("fresh-access", "wrong")
        self.assertEqual(transport.calls, [])

    def test_close_forwards_only_fresh_user_bearer_and_confirmation(self):
        provider, transport = self.provider([(200, {"closed": True})])
        provider.close_account("fresh-access", "close-account")
        method, url, headers, body = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/functions/v1/ordax-account-lifecycle/close"))
        self.assertEqual(headers["Authorization"], "Bearer fresh-access")
        self.assertEqual(headers["apikey"], "sb_publishable_1234567890")
        self.assertEqual(json.loads(body), {"confirmation": "close-account"})
        self.assertNotIn("service_role", json.dumps(headers).lower())

    def test_service_error_does_not_echo_token(self):
        provider, _ = self.provider([(503, {"error": "account-close-disabled"})])
        with self.assertRaises(lifecycle_module.SupabaseLifecycleError) as caught:
            provider.close_account("TOP-SECRET-TOKEN", "close-account")
        self.assertEqual(caught.exception.code, "account-close-disabled")
        self.assertNotIn("TOP-SECRET-TOKEN", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
