import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "project-repository-connections.json"
FOUNDATION = ROOT / "infra" / "supabase" / "product" / "migrations" / "0001_product_foundation.sql"
PROJECTS_DEVICES = ROOT / "infra" / "supabase" / "product" / "migrations" / "0006_projects_devices_remote_grants.sql"


class ProjectRepositoryConnectionsTests(unittest.TestCase):
    def test_node_contract_boundary(self):
        subprocess.run(
            ["node", "--test", "tests/test_project_repository_connections.mjs"],
            cwd=ROOT,
            check=True,
        )

    def test_existing_backend_shape_is_space_project_bound_and_token_free(self):
        foundation = FOUNDATION.read_text(encoding="utf-8")
        start = foundation.index("create table public.ordax_project_connections (")
        end = foundation.index("\n);", start) + 3
        table = foundation[start:end]

        self.assertIn("space_id uuid not null", table)
        self.assertIn("provider text not null", table)
        self.assertIn("installation_id bigint", table)
        self.assertIn("repository_id bigint", table)
        self.assertIn("repository_full_name text", table)
        self.assertNotIn("access_token", table.lower())
        self.assertNotIn("refresh_token", table.lower())
        self.assertNotIn("client_secret", table.lower())

        projects_devices = PROJECTS_DEVICES.read_text(encoding="utf-8")
        self.assertIn("alter table public.ordax_project_connections\n  add column project_id uuid;", projects_devices)
        self.assertIn("constraint ordax_project_connections_project_space_fk", projects_devices)
        self.assertIn("references public.ordax_projects(project_id, space_id)", projects_devices)

    def test_contract_preserves_direct_github_route_and_backend_secret_ownership(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        github = contract["github_policy"]
        backend = contract["backend_binding"]

        self.assertTrue(github["direct_external_model_connector_remains_first_class"])
        self.assertFalse(github["direct_external_model_connector_requires_ordax_account"])
        self.assertFalse(github["direct_external_model_connector_grants_ordax_memory"])
        self.assertFalse(github["direct_external_model_connector_grants_local_files"])
        self.assertTrue(backend["provider_specific_installation_id_backend_only"])
        self.assertTrue(backend["provider_token_backend_secret_owner_only"])
        self.assertFalse(backend["provider_token_allowed_in_surface_projection"])
        self.assertFalse(backend["client_direct_mutation_allowed"])
        self.assertFalse(backend["public_activation"])


if __name__ == "__main__":
    unittest.main()
