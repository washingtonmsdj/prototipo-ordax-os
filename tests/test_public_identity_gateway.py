import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "services" / "public-identity"
GATEWAY_PATH = SERVICE_ROOT / "gateway.py"
CONTRACT_PATH = ROOT / "docs" / "contracts" / "public-identity-gateway.json"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

spec = importlib.util.spec_from_file_location("ordax_public_identity_gateway", GATEWAY_PATH)
gateway_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gateway_module
spec.loader.exec_module(gateway_module)


class PublicIdentityGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = gateway_module.PublicIdentityGateway(
            provider=None,
            sync_provider=None,
        )

    def payload(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_contract_records_real_flow_but_keeps_runtime_provider_unconfigured(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["status"],
            "real-auth-and-account-sync-gateway-source-v7-edge-revision-8-recovery-request-fail-closed-public-server-gated",
        )
        self.assertFalse(contract["baseline"]["provider_configured"])
        self.assertTrue(contract["baseline"]["http_only_session_cookies"])
        self.assertTrue(contract["baseline"]["refresh_session_supported"])
        self.assertFalse(contract["baseline"]["tokens_in_response_body_allowed"])
        self.assertFalse(contract["baseline"]["cross_site_state_changes_allowed"])
        self.assertTrue(contract["baseline"]["csrf_state_change_protection"])
        self.assertTrue(contract["deployment"]["same_origin_adapter_source_ready"])
        self.assertFalse(contract["deployment"]["same_origin_adapter_deployed"])
        self.assertFalse(contract["deployment"]["public_browser_same_origin_activated"])
        self.assertTrue(contract["baseline"]["browser_form_redirects_implemented"])
        self.assertTrue(contract["baseline"]["json_api_mode_preserved"])
        self.assertEqual(contract["baseline"]["registration_password_minimum_chars"], 12)
        self.assertTrue(contract["baseline"]["registration_password_policy_enforced_at_edge"])
        self.assertFalse(contract["baseline"]["existing_login_passwords_retroactively_rejected"])
        self.assertEqual(contract["runtime"]["gateway_source_version"], 7)
        self.assertEqual(contract["runtime"]["edge_deployment_revision_observed"], 8)
        self.assertTrue(contract["baseline"]["public_site_server_activation_gate"])
        self.assertFalse(contract["baseline"]["public_site_account_enabled"])
        self.assertEqual(contract["baseline"]["public_site_marker_header"], "X-OrdaX-Public-Site")
        self.assertEqual(contract["baseline"]["public_site_disabled_error"], "public-account-access-disabled")
        self.assertTrue(contract["baseline"]["native_json_account_flow_remains_enabled"])
        self.assertTrue(contract["deployment"]["public_site_proxy_marker_required"])
        self.assertTrue(contract["baseline"]["password_recovery_request_implemented"])
        self.assertTrue(contract["baseline"]["password_recovery_redirect_required"])
        self.assertFalse(contract["baseline"]["password_recovery_redirect_verified"])
        self.assertFalse(contract["baseline"]["password_recovery_account_enumeration_allowed"])
        self.assertFalse(contract["baseline"]["password_recovery_completion_flow_implemented"])

    def test_marked_public_site_requests_are_server_gated(self):
        marker = {"X-OrdaX-Public-Site": "1"}

        session = self.gateway.handle("GET", "/auth/session", marker)
        self.assertEqual(session.status, 200)
        session_payload = self.payload(session)
        self.assertFalse(session_payload["authenticated"])
        self.assertEqual(session_payload["provider"], "gated")

        sync = self.gateway.handle("GET", "/sync/snapshot?limit=1", marker)
        self.assertEqual(sync.status, 503)
        self.assertEqual(self.payload(sync)["error"], "public-account-access-disabled")

    def test_session_is_anonymous_and_contains_no_tokens_without_runtime_config(self):
        response = self.gateway.handle("GET", "/auth/session")
        self.assertEqual(response.status, 200)
        payload = self.payload(response)
        self.assertFalse(payload["authenticated"])
        self.assertEqual(payload["provider"], "unconfigured")
        body = response.body.decode("utf-8").lower()
        for forbidden in ("access_token", "refresh_token", "bearer", "password"):
            self.assertNotIn(forbidden, body)
        self.assertIn(("Cache-Control", "no-store, max-age=0"), response.headers)

    def test_identity_entry_get_routes_are_canonical_same_origin_pages(self):
        cases = (
            ("/auth/login", "/login/"),
            ("/auth/register", "/cadastro/"),
        )
        for path, location in cases:
            with self.subTest(path=path):
                response = self.gateway.handle("GET", path)
                self.assertEqual(response.status, 303)
                self.assertEqual(dict(response.headers)["Location"], location)

    def test_credential_posts_fail_closed_until_provider_exists(self):
        headers = {"content-type": "application/x-www-form-urlencoded"}
        for path in ("/auth/login", "/auth/register"):
            with self.subTest(path=path):
                response = self.gateway.handle(
                    "POST",
                    path,
                    headers,
                    b"email=pessoa%40example.com&password=secret",
                )
                self.assertEqual(response.status, 503)
                self.assertEqual(
                    self.payload(response)["error"],
                    "identity-provider-unavailable",
                )

    def test_logout_is_idempotent_and_clears_local_session_cookies(self):
        response = self.gateway.handle("POST", "/auth/logout")
        self.assertEqual(response.status, 303)
        cookies = [value for key, value in response.headers if key == "Set-Cookie"]
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("HttpOnly" in value for value in cookies))
        self.assertTrue(all("Max-Age=0" in value for value in cookies))

    def test_recovery_request_is_fail_closed_without_redirect_configuration(self):
        class FakeProvider:
            def __init__(self):
                self.calls = []

            def request_password_recovery(self, email, redirect_to):
                self.calls.append((email, redirect_to))

        provider = FakeProvider()
        gateway = gateway_module.PublicIdentityGateway(
            provider=provider,
            sync_provider=None,
        )
        headers = {"content-type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, {"ORDAX_ACCOUNT_RECOVERY_REDIRECT_URL": ""}, clear=False):
            response = gateway.handle(
                "POST",
                "/auth/recover",
                headers,
                b"email=pessoa%40example.com",
            )
        self.assertEqual(response.status, 503)
        self.assertEqual(self.payload(response)["error"], "account-recovery-unavailable")
        self.assertEqual(provider.calls, [])

    def test_recovery_request_is_generic_and_uses_clean_https_redirect(self):
        class FakeProvider:
            def __init__(self):
                self.calls = []

            def request_password_recovery(self, email, redirect_to):
                self.calls.append((email, redirect_to))

        provider = FakeProvider()
        gateway = gateway_module.PublicIdentityGateway(
            provider=provider,
            sync_provider=None,
        )
        headers = {"content-type": "application/x-www-form-urlencoded"}
        with patch.dict(
            os.environ,
            {"ORDAX_ACCOUNT_RECOVERY_REDIRECT_URL": "https://accounts.ordax.example/recuperar/concluir"},
            clear=False,
        ):
            response = gateway.handle(
                "POST",
                "/auth/recover",
                headers,
                b"email=pessoa%40example.com",
            )
        self.assertEqual(response.status, 202)
        payload = self.payload(response)
        self.assertTrue(payload["recoveryRequested"])
        self.assertNotIn("exists", response.body.decode("utf-8").lower())
        self.assertEqual(
            provider.calls,
            [("pessoa@example.com", "https://accounts.ordax.example/recuperar/concluir")],
        )

    def test_marked_public_recovery_request_remains_server_gated(self):
        response = self.gateway.handle(
            "POST",
            "/auth/recover",
            {
                "X-OrdaX-Public-Site": "1",
                "content-type": "application/x-www-form-urlencoded",
            },
            b"email=pessoa%40example.com",
        )
        self.assertEqual(response.status, 503)
        self.assertEqual(self.payload(response)["error"], "public-account-access-disabled")

    def test_sync_routes_fail_closed_without_identity_provider(self):
        for path in ("/sync/snapshot", "/sync/changes", "/sync/objects"):
            with self.subTest(path=path):
                read = self.gateway.handle("GET", path)
                self.assertEqual(read.status, 503)
        write = self.gateway.handle(
            "POST",
            "/sync/mutate",
            {"content-type": "application/json"},
            b"{}",
        )
        self.assertEqual(write.status, 503)

    def test_methods_are_narrow(self):
        cases = (
            ("POST", "/auth/session", "GET"),
            ("PUT", "/auth/login", "GET, POST"),
            ("GET", "/auth/logout", "POST"),
            ("GET", "/auth/recover", "POST"),
            ("POST", "/sync/snapshot", "GET"),
            ("POST", "/sync/changes", "GET"),
            ("POST", "/sync/objects", "GET"),
            ("GET", "/sync/mutate", "POST"),
        )
        for method, path, allowed in cases:
            with self.subTest(method=method, path=path):
                response = self.gateway.handle(method, path)
                self.assertEqual(response.status, 405)
                self.assertEqual(dict(response.headers)["Allow"], allowed)

    def test_unknown_gateway_route_is_not_accepted(self):
        for path in ("/auth/admin", "/sync/admin"):
            with self.subTest(path=path):
                response = self.gateway.handle("GET", path)
                self.assertEqual(response.status, 404)
                self.assertEqual(self.payload(response)["error"], "gateway-route-not-found")

    def test_cross_site_logout_is_rejected(self):
        response = self.gateway.handle(
            "POST",
            "/auth/logout",
            {"Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(response.status, 403)
        self.assertEqual(self.payload(response)["error"], "cross-site-request-rejected")


if __name__ == "__main__":
    unittest.main()
