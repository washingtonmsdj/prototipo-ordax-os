#!/usr/bin/env python3
"""Regression tests for the pre-MVP ecosystem foundation."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

FOUNDATION = ROOT / "docs" / "contracts" / "foundation.json"
ENTITLEMENTS = ROOT / "docs" / "contracts" / "entitlements.json"
SPACES = ROOT / "docs" / "contracts" / "spaces-and-profile-packs.json"
MEMORY = ROOT / "docs" / "contracts" / "memory.json"
MODEL_ROUTER = ROOT / "docs" / "contracts" / "model-router.json"
APP_DISTRIBUTION = ROOT / "docs" / "contracts" / "app-distribution.json"
EXTERNAL_AI = ROOT / "docs" / "contracts" / "external-ai-bridge.json"
LEGAL_PACK = ROOT / "system" / "profile-packs" / "legal-br" / "manifest.json"
DEVELOPER_PACK = ROOT / "system" / "profile-packs" / "developer" / "manifest.json"
MIGRATION_1 = ROOT / "infra" / "supabase" / "product" / "migrations" / "0001_product_foundation.sql"
MIGRATION_3 = ROOT / "infra" / "supabase" / "product" / "migrations" / "0003_spaces_single_profile_pack_owner.sql"
MIGRATION_4 = ROOT / "infra" / "supabase" / "product" / "migrations" / "0004_server_authoritative_mutations.sql"
SURFACE_WORKFLOW = ROOT / ".github" / "workflows" / "surface-web-candidate.yml"


class PreMvpEcosystemFoundationTests(unittest.TestCase):
    @staticmethod
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_foundation_references_all_ecosystem_contracts(self):
        foundation = self.load(FOUNDATION)
        ecosystem = foundation["ecosystem_foundation"]
        self.assertEqual(ecosystem["status"], "pre-mvp-source-foundation")
        for relative_path in ecosystem["contracts"].values():
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)
        self.assertTrue(ecosystem["memory_owned_by_ordax"])
        self.assertFalse(ecosystem["inference_provider_owns_memory"])
        self.assertFalse(ecosystem["product_mcp_reuses_development_owner_credentials"])
        self.assertTrue(ecosystem["github_project_access_prefers_github_app"])

    def test_commercial_foundation_does_not_turn_identity_into_paywall(self):
        foundation = self.load(FOUNDATION)
        plans = foundation["plans"]
        self.assertFalse(plans["billing_implemented"])
        self.assertFalse(plans["pricing_defined"])
        self.assertFalse(plans["commercial_tiers_defined"])
        self.assertFalse(plans["identity_is_plan_gated"])
        self.assertEqual(plans["provisional_private_space_limit"], 2)
        self.assertFalse(plans["profile_pack_categories_are_plan_locked"])

        entitlements = self.load(ENTITLEMENTS)
        self.assertTrue(entitlements["principles"]["identity_is_never_plan_gated"])
        self.assertTrue(entitlements["principles"]["offline_local_os_usage_is_never_plan_gated"])
        self.assertFalse(entitlements["principles"]["client_claimed_paid_state_is_authoritative"])

    def test_professional_profile_is_a_pack_on_a_space(self):
        contract = self.load(SPACES)
        self.assertTrue(contract["ownership"]["account_profile_is_not_a_professional_profile"])
        self.assertIn("professional", contract["space_kinds"])
        self.assertFalse(contract["profile_pack"]["may_auto_grant_privilege"])
        self.assertFalse(contract["profile_pack"]["may_install_unverified_code"])
        self.assertTrue(contract["profile_pack"]["knowledge_sources_require_provenance"])
        self.assertTrue(contract["profile_pack"]["knowledge_sources_require_freshness_policy"])

    def test_legal_pack_is_draft_and_requires_fresh_authoritative_sources(self):
        pack = self.load(LEGAL_PACK)
        self.assertEqual(pack["state"], "draft")
        self.assertEqual(pack["jurisdiction"], "BR")
        self.assertFalse(pack["activation"]["publicly_available"])
        self.assertTrue(pack["knowledge"]["source_date_required"])
        self.assertTrue(pack["knowledge"]["jurisdiction_required"])
        self.assertTrue(pack["knowledge"]["citation_required_for_retrieved_authority"])
        self.assertTrue(pack["knowledge"]["stale_knowledge_must_be_identified"])
        self.assertFalse(pack["intelligence"]["model_output_is_authoritative_source"])
        self.assertFalse(pack["security"]["auto_grant_privileges"])
        self.assertFalse(pack["security"]["allow_unsigned_apps"])

    def test_developer_pack_has_no_implicit_shell_or_privilege(self):
        pack = self.load(DEVELOPER_PACK)
        self.assertEqual(pack["state"], "draft")
        self.assertFalse(pack["security"]["auto_grant_privileges"])
        self.assertFalse(pack["security"]["generic_shell_implied"])

    def test_memory_belongs_to_ordax_and_semantic_index_is_derived(self):
        memory = self.load(MEMORY)
        self.assertTrue(memory["provider_neutral"])
        self.assertFalse(memory["model_owns_memory"])
        self.assertEqual(memory["scopes"], ["device", "account", "space", "project", "session"])
        self.assertTrue(memory["requirements"]["local_first"])
        self.assertTrue(memory["requirements"]["user_can_view"])
        self.assertTrue(memory["requirements"]["user_can_edit"])
        self.assertTrue(memory["requirements"]["user_can_delete"])
        self.assertFalse(memory["requirements"]["secret_material_as_memory_allowed"])
        self.assertTrue(memory["retrieval"]["semantic_index_is_derived_and_rebuildable"])

    def test_external_models_require_explicit_egress_and_do_not_own_memory(self):
        router = self.load(MODEL_ROUTER)
        self.assertTrue(router["rules"]["external_egress_requires_policy_and_user_visibility"])
        self.assertFalse(router["rules"]["memory_is_provider_owned"])
        self.assertTrue(router["rules"]["local_ai_remains_available_when_cloud_provider_unavailable"])

    def test_store_foundation_never_bypasses_trust_or_permissions(self):
        distribution = self.load(APP_DISTRIBUTION)
        security = distribution["security"]
        self.assertFalse(security["unsigned_third_party_install_allowed"])
        self.assertFalse(security["profile_pack_may_bypass_package_verification"])
        self.assertFalse(security["profile_pack_may_auto_grant_permissions"])
        self.assertTrue(security["failed_update_preserves_working_version"])
        self.assertFalse(distribution["mvp"]["third_party_installation_enabled"])
        self.assertFalse(distribution["mvp"]["store_ui_enabled"])

    def test_product_mcp_uses_ordax_oauth_and_scoped_github_app_access(self):
        bridge = self.load(EXTERNAL_AI)
        self.assertEqual(bridge["transport"], "mcp")
        self.assertTrue(bridge["authentication"]["user_authenticates_to_ordax"])
        self.assertTrue(bridge["authentication"]["oauth_2_1_required_for_remote_clients"])
        self.assertTrue(bridge["authentication"]["pkce_required_for_public_clients"])
        self.assertFalse(bridge["authentication"]["development_owner_mcp_credentials_reusable_for_end_users"])
        self.assertEqual(bridge["project_sources"]["preferred_github_integration"], "github-app")
        self.assertTrue(bridge["project_sources"]["repository_allowlist_required"])
        self.assertFalse(bridge["project_sources"]["github_token_exposed_to_external_ai"])
        self.assertIn("generic-shell", bridge["forbidden"])
        self.assertIn("unscoped-github-account", bridge["forbidden"])

    def test_supabase_product_migration_has_rls_vector_and_no_provider_tokens(self):
        sql = MIGRATION_1.read_text(encoding="utf-8").lower()
        self.assertIn("create extension if not exists vector with schema extensions", sql)
        for table in (
            "ordax_accounts",
            "ordax_spaces",
            "ordax_space_members",
            "ordax_entitlement_grants",
            "ordax_profile_packs",
            "ordax_space_profile_packs",
            "ordax_memory_items",
            "ordax_memory_embeddings",
            "ordax_project_connections",
        ):
            self.assertIn(f"alter table public.{table} enable row level security", sql)
            self.assertIn(f"revoke all on table public.{table} from public, anon, authenticated", sql)
        for forbidden in ("github_token", "openai_api_key", "xai_api_key", "service_role_key"):
            self.assertNotIn(forbidden, sql)

    def test_space_pack_has_one_source_of_truth_and_owner_identity_is_immutable_to_client(self):
        sql = MIGRATION_3.read_text(encoding="utf-8").lower()
        self.assertIn("drop column if exists profile_pack_slug", sql)
        self.assertIn("revoke update on table public.ordax_spaces from authenticated", sql)
        self.assertIn("grant update (name, state, metadata)", sql)
        self.assertNotIn("owner_user_id)", sql)

    def test_scoped_product_mutations_are_server_authoritative(self):
        sql = MIGRATION_4.read_text(encoding="utf-8").lower()
        for table in (
            "ordax_spaces",
            "ordax_space_members",
            "ordax_memory_items",
            "ordax_memory_embeddings",
            "ordax_project_connections",
            "ordax_space_profile_packs",
            "ordax_entitlement_grants",
            "ordax_profile_packs",
        ):
            self.assertIn(
                f"revoke insert, update, delete on table public.{table} from authenticated",
                sql,
            )
        self.assertIn(
            "grant update (display_name) on table public.ordax_accounts to authenticated",
            sql,
        )


    def test_ecosystem_javascript_contracts_are_wired_into_surface_ci(self):
        workflow = SURFACE_WORKFLOW.read_text(encoding="utf-8")
        for path in (
            "system/contracts/entitlements.mjs",
            "system/contracts/spaces.mjs",
            "system/contracts/memory.mjs",
            "system/contracts/model-router.mjs",
            "tests/test_ecosystem_contracts.mjs",
        ):
            self.assertGreaterEqual(workflow.count(path), 2, path)
        self.assertIn(
            "node --test tests/test_ecosystem_contracts.mjs",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
