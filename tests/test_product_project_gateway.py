import importlib.util
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PATH = ROOT / "services" / "product-gateway" / "gateway.py"
CONTRACT_PATH = ROOT / "docs" / "contracts" / "product-project-gateway.json"

spec = importlib.util.spec_from_file_location("ordax_product_project_gateway", GATEWAY_PATH)
gateway_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gateway_module
spec.loader.exec_module(gateway_module)

ProductProjectGateway = gateway_module.ProductProjectGateway
ProductSession = gateway_module.ProductSession
MutationReceipt = gateway_module.MutationReceipt

USER_ID = "11111111-1111-4111-8111-111111111111"
SPACE_ID = "22222222-2222-4222-8222-222222222222"
PROJECT_ID = "33333333-3333-4333-8333-333333333333"
DEVICE_ID = "44444444-4444-4444-8444-444444444444"
AUDIT_ID = "55555555-5555-4555-8555-555555555555"
IDEMPOTENCY = "request-00000001"
CSRF = "csrf-secret-value"


def payload(response):
    return json.loads(response.body.decode("utf-8"))


class StaticSessions:
    configured = True

    def __init__(self, session):
        self.session = session

    def resolve(self, cookie_header):
        self.cookie_header = cookie_header
        return self.session


class RecordingAuthority:
    configured = True

    def __init__(self):
        self.calls = []

    def _receipt(self, resource_type, resource_id):
        return MutationReceipt(
            resource_type=resource_type,
            resource_id=resource_id,
            audit_id=AUDIT_ID,
            entitlements_checked=True,
            approval_checked=True,
        )

    def create_project(self, **kwargs):
        self.calls.append(("create_project", kwargs))
        return self._receipt("project", PROJECT_ID)

    def bind_project_device(self, **kwargs):
        self.calls.append(("bind_project_device", kwargs))
        return self._receipt("project-binding", PROJECT_ID)

    def grant_remote_capability(self, **kwargs):
        self.calls.append(("grant_remote_capability", kwargs))
        return self._receipt("remote-grant", PROJECT_ID)


def authenticated_gateway(authority=None):
    sessions = StaticSessions(
        ProductSession(
            authenticated=True,
            user_id=USER_ID,
            csrf_token=CSRF,
        )
    )
    return ProductProjectGateway(
        sessions=sessions,
        authority=authority or RecordingAuthority(),
    )


def post_headers(**overrides):
    headers = {
        "Content-Type": "application/json",
        "Cookie": "ordax_session=opaque",
        "X-OrdaX-CSRF": CSRF,
        "Idempotency-Key": IDEMPOTENCY,
        "Sec-Fetch-Site": "same-origin",
    }
    headers.update(overrides)
    return headers


class ProductProjectGatewayTests(unittest.TestCase):
    def test_default_gateway_is_fail_closed_and_status_exposes_no_secret(self):
        gateway = ProductProjectGateway()
        response = gateway.handle("GET", "/product/status")
        self.assertEqual(response.status, 200)
        body = payload(response)
        self.assertFalse(body["identity_configured"])
        self.assertFalse(body["authority_configured"])
        self.assertFalse(body["mutations_enabled"])
        self.assertNotIn("key", json.dumps(body).lower())
        self.assertNotIn("token", json.dumps(body).lower())

        mutation = gateway.handle(
            "POST",
            "/product/projects",
            {"Content-Type": "application/json"},
            b'{"space_id":"x","name":"x","kind":"general"}',
        )
        self.assertEqual(mutation.status, 401)
        self.assertEqual(payload(mutation)["error"], "authentication-required")

    def test_mutation_rejects_cross_site_before_session_or_authority(self):
        gateway = authenticated_gateway()
        response = gateway.handle(
            "POST",
            "/product/projects",
            post_headers(**{"Sec-Fetch-Site": "cross-site"}),
            b"{}",
        )
        self.assertEqual(response.status, 403)
        self.assertEqual(payload(response)["error"], "cross-site-request-rejected")

    def test_mutation_requires_csrf_and_idempotency(self):
        authority = RecordingAuthority()
        gateway = authenticated_gateway(authority)

        no_csrf = post_headers()
        no_csrf.pop("X-OrdaX-CSRF")
        response = gateway.handle("POST", "/product/projects", no_csrf, b"{}")
        self.assertEqual(response.status, 403)
        self.assertEqual(authority.calls, [])

        no_idempotency = post_headers()
        no_idempotency.pop("Idempotency-Key")
        response = gateway.handle("POST", "/product/projects", no_idempotency, b"{}")
        self.assertEqual(response.status, 400)
        self.assertEqual(authority.calls, [])

    def test_create_project_delegates_only_valid_bounded_values(self):
        authority = RecordingAuthority()
        gateway = authenticated_gateway(authority)
        body = json.dumps(
            {"space_id": SPACE_ID, "name": "  Projeto A  ", "kind": "development"}
        ).encode("utf-8")

        response = gateway.handle("POST", "/product/projects", post_headers(), body)
        self.assertEqual(response.status, 201)
        self.assertEqual(
            authority.calls,
            [
                (
                    "create_project",
                    {
                        "user_id": USER_ID,
                        "space_id": SPACE_ID,
                        "name": "Projeto A",
                        "kind": "development",
                        "idempotency_key": IDEMPOTENCY,
                    },
                )
            ],
        )
        receipt = payload(response)
        self.assertTrue(receipt["entitlements_checked"])
        self.assertTrue(receipt["approval_checked"])
        self.assertEqual(receipt["audit_id"], AUDIT_ID)

    def test_project_binding_rejects_filesystem_paths_and_forbidden_capabilities(self):
        authority = RecordingAuthority()
        gateway = authenticated_gateway(authority)

        for local_ref in (
            "/home/user/project",
            r"C:\Users\user\project",
            "../project",
            "folder/project",
        ):
            body = json.dumps(
                {
                    "project_id": PROJECT_ID,
                    "device_id": DEVICE_ID,
                    "local_project_ref": local_ref,
                    "allowed_capabilities": ["project.read-context"],
                }
            ).encode("utf-8")
            response = gateway.handle(
                "POST", "/product/project-bindings", post_headers(), body
            )
            self.assertEqual(response.status, 400)

        dangerous = json.dumps(
            {
                "project_id": PROJECT_ID,
                "device_id": DEVICE_ID,
                "local_project_ref": "project-1",
                "allowed_capabilities": ["generic-shell"],
            }
        ).encode("utf-8")
        response = gateway.handle(
            "POST", "/product/project-bindings", post_headers(), dangerous
        )
        self.assertEqual(response.status, 400)
        self.assertEqual(authority.calls, [])

    def test_remote_grant_rejects_high_risk_authority_before_adapter(self):
        authority = RecordingAuthority()
        gateway = authenticated_gateway(authority)
        for capability in (
            "generic-shell",
            "raw-disk",
            "release-signing-key",
            "implicit-admin",
            "cross-user-memory",
            "cross-space-memory",
            "unscoped-github-account",
        ):
            body = json.dumps(
                {
                    "space_id": SPACE_ID,
                    "project_id": PROJECT_ID,
                    "device_id": DEVICE_ID,
                    "client_kind": "product-mcp",
                    "capability": capability,
                    "access_mode": "write",
                }
            ).encode("utf-8")
            response = gateway.handle(
                "POST", "/product/remote-grants", post_headers(), body
            )
            self.assertEqual(response.status, 400, capability)
        self.assertEqual(authority.calls, [])

    def test_valid_remote_grant_is_scoped_and_audited(self):
        authority = RecordingAuthority()
        gateway = authenticated_gateway(authority)
        body = json.dumps(
            {
                "space_id": SPACE_ID,
                "project_id": PROJECT_ID,
                "device_id": DEVICE_ID,
                "client_kind": "product-mcp",
                "capability": "project.read-context",
                "access_mode": "read",
            }
        ).encode("utf-8")
        response = gateway.handle(
            "POST", "/product/remote-grants", post_headers(), body
        )
        self.assertEqual(response.status, 201)
        self.assertEqual(authority.calls[0][0], "grant_remote_capability")
        call = authority.calls[0][1]
        self.assertEqual(call["user_id"], USER_ID)
        self.assertEqual(call["space_id"], SPACE_ID)
        self.assertEqual(call["project_id"], PROJECT_ID)
        self.assertEqual(call["device_id"], DEVICE_ID)
        self.assertEqual(call["capability"], "project.read-context")
        self.assertEqual(call["access_mode"], "read")

    def test_authority_receipt_must_prove_entitlement_approval_and_audit(self):
        class BadAuthority(RecordingAuthority):
            def create_project(self, **kwargs):
                self.calls.append(("create_project", kwargs))
                return MutationReceipt(
                    resource_type="project",
                    resource_id=PROJECT_ID,
                    audit_id=AUDIT_ID,
                    entitlements_checked=False,
                    approval_checked=True,
                )

        gateway = authenticated_gateway(BadAuthority())
        body = json.dumps(
            {"space_id": SPACE_ID, "name": "Projeto", "kind": "general"}
        ).encode("utf-8")
        response = gateway.handle("POST", "/product/projects", post_headers(), body)
        self.assertEqual(response.status, 502)
        self.assertEqual(payload(response)["error"], "invalid-authority-receipt")

    def test_contract_keeps_public_activation_disabled_and_service_role_out_of_client(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertTrue(contract["backend"]["provider_neutral"])
        self.assertFalse(contract["backend"]["supabase_service_role_in_client"])
        self.assertFalse(contract["backend"]["public_activation"])
        self.assertTrue(contract["session"]["csrf_required_for_mutation"])
        self.assertIn("generic-shell", contract["forbidden_capabilities"])
        self.assertIn("release-signing-key", contract["forbidden_capabilities"])


if __name__ == "__main__":
    unittest.main()
