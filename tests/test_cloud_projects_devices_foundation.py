import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "cloud-projects-devices.json"
MIGRATION = (
    ROOT
    / "infra"
    / "supabase"
    / "product"
    / "migrations"
    / "0006_projects_devices_remote_grants.sql"
)
INDEX_MIGRATION = (
    ROOT
    / "infra"
    / "supabase"
    / "product"
    / "migrations"
    / "0007_projects_devices_fk_indexes.sql"
)


class CloudProjectsDevicesFoundationTests(unittest.TestCase):
    def test_contract_keeps_cloud_provider_neutral_and_local_files_opt_in(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["domain"]["backend_name"], "OrdaX Cloud")
        self.assertEqual(contract["domain"]["current_backend_adapter"], "supabase")
        self.assertFalse(contract["domain"]["supabase_is_user_visible_identity"])
        self.assertFalse(contract["projects"]["local_path_stored_in_cloud"])
        self.assertTrue(contract["projects"]["local_device_binding_uses_opaque_ref"])
        self.assertFalse(contract["storage"]["all_local_files_uploaded_by_default"])
        self.assertFalse(contract["storage"]["github_code_duplicated_to_supabase_by_default"])
        self.assertTrue(contract["storage"]["cloud_file_sync_is_opt_in"])

    def test_product_device_registry_does_not_reuse_engineering_device_authority(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("create table public.ordax_product_devices", sql)
        self.assertNotIn("create table public.ordax_devices (", sql)
        self.assertIn("separate from engineering public.ordax_devices", sql)
        self.assertIn("create table public.ordax_device_presence", sql)

    def test_projects_become_first_class_and_connections_bind_to_project(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("create table public.ordax_projects", sql)
        self.assertIn("add column project_id uuid", sql)
        self.assertIn("alter column project_id set not null", sql)
        self.assertIn("unique (project_id, space_id)", sql)
        self.assertIn("ordax_project_connections_project_space_fk", sql)
        self.assertIn(
            "foreign key (project_id, space_id)",
            sql,
        )

    def test_remote_grants_are_server_authoritative_and_no_generic_shell_exists(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertFalse(contract["authority"]["authenticated_clients_can_directly_mutate_scoped_resources"])
        self.assertFalse(contract["remote_access"]["generic_shell_grant_supported"])

        sql = MIGRATION.read_text(encoding="utf-8").lower()
        self.assertIn("create table public.ordax_remote_capability_grants", sql)
        self.assertIn("grant select on table public.ordax_remote_capability_grants to authenticated", sql)
        self.assertNotIn(
            "grant insert, update, delete on table public.ordax_remote_capability_grants to authenticated",
            sql,
        )

    def test_all_new_product_tables_enable_rls_and_revoke_anon(self):
        sql = MIGRATION.read_text(encoding="utf-8").lower()
        tables = (
            "ordax_projects",
            "ordax_product_devices",
            "ordax_device_presence",
            "ordax_space_devices",
            "ordax_device_project_bindings",
            "ordax_remote_capability_grants",
        )
        for table in tables:
            self.assertIn(f"alter table public.{table} enable row level security", sql)
            self.assertIn(f"revoke all on table public.{table}", sql)

    def test_cloud_binding_ref_rejects_paths(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("local_project_ref !~ '[\\\\/]'", sql)
        self.assertIn("local_project_ref !~ '\\.\\.'", sql)

    def test_product_foreign_keys_have_explicit_covering_indexes(self):
        sql = INDEX_MIGRATION.read_text(encoding="utf-8").lower()
        for index_name in (
            "ordax_project_connections_project_space_idx",
            "ordax_remote_grants_project_space_idx",
            "ordax_remote_grants_device_idx",
            "ordax_remote_grants_approved_by_idx",
            "ordax_space_devices_granted_by_idx",
        ):
            self.assertIn(index_name, sql)


if __name__ == "__main__":
    unittest.main()
