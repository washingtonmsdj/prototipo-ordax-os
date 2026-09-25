import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_CONTRACT = ROOT / "docs" / "contracts" / "sync-model.json"
SYNC_MIGRATION = ROOT / "infra" / "supabase" / "product" / "migrations" / "20260925004439_account_sync_objects_v1.sql"
GATEWAY = ROOT / "services" / "public-identity" / "gateway.py"
EDGE_GATEWAY = ROOT / "infra" / "supabase" / "functions" / "ordax-account-gateway" / "index.ts"
NATIVE_GATEWAY_CONFIG = ROOT / "system" / "services" / "account" / "gateway-base-url"
CURSOR_MIGRATION = ROOT / "infra" / "supabase" / "product" / "migrations" / "20260925013355_account_sync_incremental_cursor_v1.sql"
SNAPSHOT_MIGRATION = ROOT / "infra" / "supabase" / "product" / "migrations" / "20260925013524_account_sync_atomic_snapshot_v1.sql"
TWO_CLIENT_PROOF = ROOT / "tools" / "account-sync" / "prove_two_clients.py"
SESSION_REVOCATION_PROOF = ROOT / "tools" / "account-sync" / "prove_session_revocation.py"


class AccountSyncAndIdentityV1Tests(unittest.TestCase):
    def test_sync_contract_records_applied_backend_without_claiming_public_rollout(self):
        contract = json.loads(SYNC_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["backend"]["status"], "applied")
        self.assertTrue(contract["backend"]["rls_owner_scoped"])
        self.assertTrue(contract["backend"]["idempotent_mutations"])
        self.assertTrue(contract["backend"]["optimistic_conflict_detection"])
        self.assertFalse(contract["mvp_availability"]["synchronization_available"])
        self.assertTrue(contract["mvp_availability"]["client_integration_available"])
        self.assertTrue(contract["backend"]["incremental_cursor_implemented"])
        self.assertEqual(
            contract["backend"]["current_read_mode"],
            "atomic-snapshot-plus-paged-incremental-cursor",
        )

    def test_sync_store_is_owner_scoped_and_mutations_are_server_authoritative(self):
        sql = SYNC_MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("alter table public.ordax_sync_objects enable row level security", sql)
        self.assertIn("(select auth.uid()) = owner_user_id", sql)
        self.assertIn("unique (owner_user_id, idempotency_key)", sql)
        self.assertIn("server_revision", sql)
        self.assertIn("tombstone", sql)
        private_sql = (ROOT / "infra" / "supabase" / "product" / "migrations" / "20260925004832_account_sync_private_store_v1.sql").read_text(encoding="utf-8").lower()
        self.assertIn("alter table public.ordax_sync_objects set schema private", private_sql)
        self.assertIn("security invoker", private_sql)
        self.assertIn("set search_path = ''", private_sql)
        self.assertIn("revoke all on function public.ordax_apply_sync_mutation_v1", private_sql)
        self.assertIn("grant execute on function public.ordax_apply_sync_mutation_v1", private_sql)
        self.assertIn("public.ordax_list_sync_objects_v1", private_sql)
        self.assertNotIn("security definer", private_sql)

    def test_incremental_cursor_and_atomic_snapshot_are_source_controlled(self):
        cursor_sql = CURSOR_MIGRATION.read_text(encoding="utf-8").lower()
        snapshot_sql = SNAPSHOT_MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("change_seq bigint generated always as identity", cursor_sql)
        self.assertIn("ordax_apply_sync_mutation_v2", cursor_sql)
        self.assertIn("ordax_pull_sync_changes_v1", cursor_sql)
        self.assertIn("security invoker", cursor_sql)
        self.assertIn("ordax_sync_snapshot_v1", snapshot_sql)
        self.assertIn("security invoker", snapshot_sql)
        self.assertNotIn("security definer", cursor_sql)
        self.assertNotIn("security definer", snapshot_sql)

    def test_deployed_edge_gateway_source_uses_user_auth_and_rls_without_service_role(self):
        text = EDGE_GATEWAY.read_text(encoding="utf-8")
        self.assertIn('ordax-account-gateway', text)
        self.assertIn('signInWithPassword', text)
        self.assertIn('refreshSession', text)
        self.assertIn('ordax_apply_sync_mutation_v2', text)
        self.assertIn('ordax_sync_snapshot_v1', text)
        self.assertIn('ordax_pull_sync_changes_v1', text)
        self.assertIn('crossSiteStateChange', text)
        self.assertIn('sec-fetch-site', text)
        self.assertIn('cross-site-request-rejected', text)
        self.assertIn('x-forwarded-host', text)
        self.assertIn('redirectResponse', text)
        self.assertIn('wantsJson', text)
        self.assertIn('path === "/auth/login" && req.method === "GET"', text)
        self.assertIn('path === "/auth/register" && req.method === "GET"', text)
        self.assertIn('redirectResponse("/conta/", cookies)', text)
        self.assertIn("MIN_REGISTRATION_PASSWORD_CHARS = 12", text)
        self.assertIn("registration-password-policy", text)
        self.assertIn("ORDAX_ACCOUNT_RECOVERY_REDIRECT_URL", text)
        self.assertIn("resetPasswordForEmail", text)
        self.assertIn('path === "/auth/recover" && req.method === "POST"', text)
        self.assertIn("account-recovery-unavailable", text)
        self.assertIn("account-recovery-rate-limited", text)
        self.assertIn("PUBLIC_SITE_ACCOUNT_ENABLED = false", text)
        self.assertIn("x-ordax-public-site", text)
        self.assertIn("publicSiteRequest", text)
        self.assertIn("public-account-access-disabled", text)
        self.assertIn('Accept', (ROOT / "system" / "surface" / "runtime" / "native_account_gateway.py").read_text(encoding="utf-8"))
        self.assertNotIn('service_role', text.lower())
        self.assertNotIn('SUPABASE_SERVICE_ROLE_KEY', text)

    def test_native_signed_gateway_config_targets_https_edge_gateway(self):
        value = NATIVE_GATEWAY_CONFIG.read_text(encoding="utf-8").strip()
        self.assertTrue(value.startswith("https://"))
        self.assertIn("/functions/v1/ordax-account-gateway", value)
        self.assertNotIn("?", value)
        self.assertNotIn("#", value)

    def test_two_client_proof_never_embeds_or_prints_account_credentials(self):
        text = TWO_CLIENT_PROOF.read_text(encoding="utf-8")
        self.assertIn("ORDAX_PROOF_ACCOUNT_EMAIL", text)
        self.assertIn("ORDAX_PROOF_ACCOUNT_PASSWORD", text)
        self.assertIn("ACCOUNT_SYNC_TWO_CLIENT_PROOF=PASS", text)
        self.assertIn("proof/two-client/", text)
        self.assertNotIn("print(password", text)
        self.assertNotIn("print(email", text)
        self.assertNotIn("service_role", text.lower())

    def test_session_revocation_proof_keeps_credentials_and_tokens_ephemeral(self):
        text = SESSION_REVOCATION_PROOF.read_text(encoding="utf-8")
        self.assertIn("ORDAX_PROOF_ACCOUNT_EMAIL", text)
        self.assertIn("ORDAX_PROOF_ACCOUNT_PASSWORD", text)
        self.assertIn("ACCOUNT_SESSION_REVOCATION_PROOF=PASS", text)
        self.assertIn("revoked-refresh-token-restored-session", text)
        self.assertIn("session-b-was-revoked-by-local-logout", text)
        self.assertNotIn("print(refresh_a", text)
        self.assertNotIn("print(password", text)
        self.assertNotIn("service_role", text.lower())

    def test_identity_gateway_keeps_provider_tokens_out_of_browser_javascript(self):
        text = GATEWAY.read_text(encoding="utf-8")
        self.assertIn("HttpOnly", text)
        self.assertIn("SameSite=Lax", text)
        self.assertIn("ORDAX_SUPABASE_PUBLISHABLE_KEY", text)
        self.assertNotIn("service_role", text.lower())
        self.assertIn("refresh_session", text)
        self.assertIn("sign_in_with_password", text)
        self.assertIn("sign_up_with_password", text)


if __name__ == "__main__":
    unittest.main()
