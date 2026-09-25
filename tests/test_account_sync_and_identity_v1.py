import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_CONTRACT = ROOT / "docs" / "contracts" / "sync-model.json"
SYNC_MIGRATION = ROOT / "infra" / "supabase" / "product" / "migrations" / "20260925004439_account_sync_objects_v1.sql"
GATEWAY = ROOT / "services" / "public-identity" / "gateway.py"


class AccountSyncAndIdentityV1Tests(unittest.TestCase):
    def test_sync_contract_records_applied_backend_without_claiming_public_rollout(self):
        contract = json.loads(SYNC_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["backend"]["status"], "applied")
        self.assertTrue(contract["backend"]["rls_owner_scoped"])
        self.assertTrue(contract["backend"]["idempotent_mutations"])
        self.assertTrue(contract["backend"]["optimistic_conflict_detection"])
        self.assertFalse(contract["mvp_availability"]["synchronization_available"])
        self.assertFalse(contract["mvp_availability"]["client_integration_available"])

    def test_sync_store_is_owner_scoped_and_mutations_are_server_authoritative(self):
        sql = SYNC_MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("alter table public.ordax_sync_objects enable row level security", sql)
        self.assertIn("(select auth.uid()) = owner_user_id", sql)
        self.assertIn("unique (owner_user_id, idempotency_key)", sql)
        self.assertIn("server_revision", sql)
        self.assertIn("tombstone", sql)
        self.assertIn("security definer", sql)
        self.assertIn("set search_path = ''", sql)
        self.assertIn("revoke all on function public.ordax_apply_sync_mutation_v1", sql)
        self.assertIn("grant execute on function public.ordax_apply_sync_mutation_v1", sql)
        self.assertNotIn("grant insert on table public.ordax_sync_objects to authenticated", sql)
        self.assertNotIn("grant update on table public.ordax_sync_objects to authenticated", sql)

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
