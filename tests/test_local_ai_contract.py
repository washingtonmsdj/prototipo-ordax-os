import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCAL_AI = ROOT / "docs" / "contracts" / "local-ai.json"
CREATOR_SELECTION = ROOT / "docs" / "contracts" / "creator-feature-selection.json"
APP = ROOT / "system" / "apps" / "assistant" / "app.mjs"
COMPONENT = ROOT / "system" / "apps" / "assistant" / "component.mjs"
CATALOG = ROOT / "system" / "apps" / "catalog.mjs"
COMPONENT_CATALOG = ROOT / "system" / "apps" / "component-catalog.mjs"


class LocalAiContractTests(unittest.TestCase):
    def test_local_ai_is_optional_local_first_and_provider_replaceable(self):
        contract = json.loads(LOCAL_AI.read_text(encoding="utf-8"))
        self.assertEqual(contract["$schema"], "prototype-ordax.local-ai/1")
        self.assertTrue(contract["principles"]["local_first"])
        self.assertTrue(contract["principles"]["works_without_account"])
        self.assertTrue(contract["principles"]["provider_and_model_replaceable"])
        self.assertFalse(contract["principles"]["shell_execution_allowed"])
        self.assertFalse(contract["principles"]["raw_disk_access_allowed"])
        self.assertEqual(contract["component"]["criticality"], "optional")
        self.assertEqual(contract["component"]["failure_domain"], "app")
        self.assertTrue(contract["migration"]["engine_identity_is_configuration"])
        self.assertTrue(contract["migration"]["model_identity_is_configuration"])
        self.assertFalse(contract["mvp_scope"]["autonomous_admin_agent"])

    def test_creator_defaults_ai_on_but_keeps_first_authorized_writer_unchanged(self):
        selection = json.loads(CREATOR_SELECTION.read_text(encoding="utf-8"))
        feature = next(item for item in selection["features"] if item["id"] == "local-ai")
        self.assertTrue(feature["default_selected"])
        self.assertTrue(feature["user_toggleable"])
        self.assertFalse(feature["required"])
        self.assertTrue(selection["rules"]["checked_feature_requires_verified_signed_package"])
        self.assertTrue(selection["physical_writer"]["current_first_proof_context_is_preserved"])
        self.assertTrue(selection["physical_writer"]["current_authorized_writer_is_not_modified_by_this_contract"])
        self.assertTrue(selection["physical_writer"]["binding_required_before_public_creator_exposure"])

    def test_assistant_is_registered_as_optional_component_slot_app(self):
        app = APP.read_text(encoding="utf-8")
        component = COMPONENT.read_text(encoding="utf-8")
        catalog = CATALOG.read_text(encoding="utf-8")
        component_catalog = COMPONENT_CATALOG.read_text(encoding="utf-8")
        self.assertIn('id: "assistant"', app)
        self.assertIn('"ai.local"', app)
        self.assertIn('releaseMode: "component-slot"', component)
        self.assertIn('criticality: "optional"', component)
        self.assertIn("assistantApp", catalog)
        self.assertIn("assistantComponent", component_catalog)


if __name__ == "__main__":
    unittest.main()
