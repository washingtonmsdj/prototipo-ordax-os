import importlib.util
import json
import sys
import unittest
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
            "real-auth-and-account-sync-gateway-v2-deployed-public-same-origin-activation-gated",
        )
        self.assertFalse(contract["baseline"]["provider_configured"])
        self.assertTrue(contract["baseline"]["http_only_session_cookies"])
        self.assertTrue(contract["baseline"]["refresh_session_supported"])
        self.assertFalse(contract["baseline"]["tokens_in_response_body_allowed"])

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
