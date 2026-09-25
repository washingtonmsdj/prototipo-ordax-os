import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "public-site-deployment.json"
NGINX = ROOT / "deploy" / "public-site" / "nginx.conf"


class PublicSiteDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.nginx = NGINX.read_text(encoding="utf-8")

    def test_contract_records_host_neutral_same_origin_adapter_without_claiming_deployment(self):
        self.assertEqual(
            self.contract["status"],
            "host-neutral-same-origin-adapter-source-ready-not-deployed",
        )
        self.assertEqual(
            self.contract["adapter"]["kind"],
            "nginx-loopback-behind-https-terminator",
        )
        self.assertFalse(self.contract["adapter"]["public_listener_in_adapter_allowed"])
        self.assertFalse(self.contract["adapter"]["provider_specific_browser_api"])
        self.assertTrue(self.contract["routing"]["same_origin_identity_required"])
        self.assertTrue(self.contract["routing"]["same_origin_sync_required"])
        self.assertIn("/conta/", self.contract["routing"]["static_routes"])

    def test_adapter_is_loopback_only_and_routes_only_account_prefixes_to_gateway(self):
        self.assertIn("listen 127.0.0.1:8080;", self.nginx)
        self.assertIn("location ~ ^/(auth|sync)/", self.nginx)
        self.assertIn(
            "/functions/v1/ordax-account-gateway$1",
            self.nginx,
        )
        self.assertIn("try_files $uri $uri/index.html =404;", self.nginx)
        self.assertNotIn("listen 0.0.0.0", self.nginx)
        self.assertNotIn("service_role", self.nginx.lower())

    def test_adapter_preserves_same_origin_security_and_no_store_account_routes(self):
        for name, value in self.contract["security_headers"].items():
            self.assertIn(name, self.nginx)
            self.assertIn(value, self.nginx)
        self.assertIn('~^/(auth|sync)/ "no-store";', self.nginx)
        self.assertIn("proxy_hide_header Access-Control-Allow-Origin;", self.nginx)
        self.assertIn("proxy_hide_header Cache-Control;", self.nginx)
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", self.nginx)
        self.assertIn("proxy_set_header X-Forwarded-Host $host;", self.nginx)

    def test_public_activation_still_requires_auth_and_legal_hardening(self):
        requirements = self.contract["production_requirements"]
        self.assertTrue(requirements["https"])
        self.assertTrue(requirements["host_adapter_must_preserve_session_set_cookie"])
        self.assertTrue(requirements["final_legal_documents_required_before_identity_activation"])
        self.assertTrue(requirements["leaked_password_protection_required_before_identity_activation"])


if __name__ == "__main__":
    unittest.main()
