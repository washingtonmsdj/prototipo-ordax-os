import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_STATE = ROOT / "docs" / "CURRENT-STATE.md"
AGENTS = ROOT / "AGENTS.md"
UPDATE_DOC = ROOT / "docs" / "UPDATE-NOMENCLATURE.md"
INTERNET_DOC = ROOT / "docs" / "INTERNET-APP.md"
PROMOTION_GATES = ROOT / "docs" / "PROMOTION-GATES.md"
UPDATE_CONTRACT = ROOT / "docs" / "contracts" / "update-nomenclature.json"
PRODUCT_VERSION = ROOT / "system" / "contracts" / "product-version.mjs"
BUNDLED_APP_MANIFESTS = ROOT / "system" / "services" / "components" / "manifests" / "apps.mjs"
PHYSICAL_SEED = ROOT / "docs" / "contracts" / "physical-media.json"
PHYSICAL_PREPARED = ROOT / "docs" / "contracts" / "physical-prepared-media.json"


def assignment_map(text):
    values = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith(("#", " ", "\t")):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Z0-9_]+", key):
            values[key] = value.strip()
    return values


def field(text, name):
    match = re.search(rf'{re.escape(name)}:\s*"([^"]+)"', text)
    if not match:
        raise AssertionError(f"missing {name} in source")
    return match.group(1)


def bundled_apps():
    text = BUNDLED_APP_MANIFESTS.read_text(encoding="utf-8")
    result = {}
    for match in re.finditer(r"defineComponentManifest\(\{(?P<body>.*?)\n\}\);", text, re.S):
        body = match.group("body")
        app_id = field(body, "id")
        result[app_id] = {
            "version": field(body, "version"),
            "release_mode": field(body, "releaseMode"),
        }
    return result


def app_owned_manifest(app_id):
    version_text = (ROOT / "system" / "apps" / app_id / "version.mjs").read_text(encoding="utf-8")
    version_match = re.search(r'=\s*"([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)"', version_text)
    if not version_match:
        raise AssertionError(f"missing version for {app_id}")
    component_text = (ROOT / "system" / "apps" / app_id / "component.mjs").read_text(encoding="utf-8")
    return {
        "version": version_match.group(1),
        "release_mode": field(component_text, "releaseMode"),
    }


def expected_apps():
    result = bundled_apps()
    result["internet"] = app_owned_manifest("internet")
    result["notes"] = app_owned_manifest("notes")
    return result


class CanonicalDocumentFreshnessTests(unittest.TestCase):
    def test_product_version_snapshot_matches_runtime_and_contract(self):
        state = assignment_map(CURRENT_STATE.read_text(encoding="utf-8"))
        product = PRODUCT_VERSION.read_text(encoding="utf-8")
        contract = json.loads(UPDATE_CONTRACT.read_text(encoding="utf-8"))
        semantic = field(product, "semanticVersion")
        display = field(product, "displayVersion")

        self.assertEqual(state["PRODUCT_VERSION"], semantic)
        self.assertEqual(state["PRODUCT_VERSION_LABEL"], display)
        self.assertEqual(contract["product_version"]["current"], semantic)
        self.assertEqual(contract["product_version"]["display"], display)

    def test_first_party_app_snapshot_matches_real_manifests(self):
        state = assignment_map(CURRENT_STATE.read_text(encoding="utf-8"))
        apps = expected_apps()
        self.assertEqual(set(apps), {"files", "settings", "account", "system", "internet", "notes"})

        for app_id, app in apps.items():
            prefix = f"APP_{app_id.upper()}"
            self.assertEqual(state[f"{prefix}_VERSION"], app["version"])
            self.assertEqual(state[f"{prefix}_RELEASE_MODE"], app["release_mode"])
            expected_maturity = "BETA" if int(app["version"].split(".", 1)[0]) == 0 else "STABLE"
            self.assertEqual(state[f"{prefix}_MATURITY"], expected_maturity)

    def test_internet_app_doc_tracks_app_owned_version_and_release_mode(self):
        internet = app_owned_manifest("internet")
        document = INTERNET_DOC.read_text(encoding="utf-8")
        self.assertIn(internet["version"], document)
        self.assertIn(f'releaseMode: "{internet["release_mode"]}"', document)
        self.assertNotIn("Internet remains `bundled`", document)

    def test_physical_snapshot_distinguishes_seed_from_prepared_usb(self):
        state = assignment_map(CURRENT_STATE.read_text(encoding="utf-8"))
        seed = json.loads(PHYSICAL_SEED.read_text(encoding="utf-8"))
        prepared = json.loads(PHYSICAL_PREPARED.read_text(encoding="utf-8"))
        seed_names = ",".join(partition["name"] for partition in seed["partitions"])
        prepared_names = ",".join(partition["name"] for partition in prepared["partitions"])

        self.assertEqual(state["BOOTSTRAP_SEED_PARTITIONS"], str(len(seed["partitions"])))
        self.assertEqual(state["BOOTSTRAP_SEED_PARTITION_NAMES"], seed_names)
        self.assertEqual(state["PREPARED_USB_PARTITIONS"], str(len(prepared["partitions"])))
        self.assertEqual(state["PREPARED_USB_PARTITION_NAMES"], prepared_names)

    def test_version_identity_is_not_confused_with_independent_delivery(self):
        contract = json.loads(UPDATE_CONTRACT.read_text(encoding="utf-8"))
        component = contract["component_version"]
        self.assertTrue(component["identity_independent_from_release_mode"])
        self.assertFalse(component["version_identity_requires_independent_packaging"])
        self.assertEqual(component["development_app_release_mode"], "git-app")
        self.assertEqual(component["independent_update_release_mode"], "component-slot")
        self.assertEqual(component["first_party_pre_1_0_maturity"], "beta")
        self.assertEqual(component["independent_components_currently_enabled_scope"], "production-component-slot-only")

    def test_promotion_gates_separate_development_proof_from_canonical_stable(self):
        state = assignment_map(CURRENT_STATE.read_text(encoding="utf-8"))
        promotion = assignment_map(PROMOTION_GATES.read_text(encoding="utf-8"))

        self.assertEqual(state["WEB_CLIENT_CANDIDATE"], "PASS")
        self.assertEqual(promotion["WEB_MODE"], "PASS_SOURCE_BROWSER_CANDIDATE")

        self.assertEqual(state["NATIVE_GRAPHICAL_HOST"], "PASS_PHYSICAL_DEVELOPMENT_USB")
        self.assertEqual(promotion["NATIVE_GRAPHICAL_MODE"], "PASS_PHYSICAL_DEVELOPMENT_USB")
        self.assertEqual(promotion["CANONICAL_STABLE_GRAPHICAL_MODE"], "PENDING")

        self.assertEqual(state["GIT_HOT_UPDATE_ROUND_TRIP"], "PASS")
        self.assertEqual(promotion["DEVELOPMENT_DEVICE_GIT_HOT_UPDATE"], "PASS_PHYSICAL_DEVELOPMENT_USB")
        self.assertEqual(promotion["STABLE_DEVICE_RELEASE_OR_DELTA_UPDATE"], "PENDING")

        self.assertEqual(promotion["MVP_SURFACE_SMOKE_HARNESS"], "PASS_SOURCE")
        self.assertEqual(promotion["MVP_SURFACE_SMOKE_PHYSICAL"], "PENDING")
        self.assertEqual(promotion["CANONICAL_RELEASE_TRUST"], "PENDING_CANONICAL_KEY")
        self.assertEqual(promotion["PHYSICAL_USB_WRITE"], "NO")

    def test_known_stale_promotion_claims_cannot_return(self):
        promotion = PROMOTION_GATES.read_text(encoding="utf-8")
        for phrase in (
            "PHYSICAL_KERNEL_BOOT=PENDING\n",
            "NOTEBOOK_UEFI_BOOT=PENDING\n",
            "WEB_MODE=PENDING\n",
            "NATIVE_GRAPHICAL_MODE=PENDING\n",
            "SAME_COMMIT_VISUAL_CHANGE=PENDING\n",
            "EDIT_SOURCE=PENDING_END_TO_END\n",
            "WEB_PREVIEW=PENDING\n",
            "DEVICE_RELEASE_OR_DELTA_UPDATE=PENDING_PHYSICAL\n",
            "HEALTH_READINESS=PENDING\n",
        ):
            self.assertNotIn(phrase, promotion)

    def test_known_stale_version_claims_cannot_return(self):
        current = CURRENT_STATE.read_text(encoding="utf-8")
        agents = AGENTS.read_text(encoding="utf-8")
        nomenclature = UPDATE_DOC.read_text(encoding="utf-8")

        forbidden_current = (
            "continue to share the product version",
            "continues to share the product release/version",
            "currently bundled with the product rather than a Surface/system subsystem",
            "instead of static placeholders",
        )
        for phrase in forbidden_current:
            self.assertNotIn(phrase, current)

        self.assertNotIn(
            "componentes não recebem número próprio enquanto não tiverem empacotamento e ciclo de release independentes",
            agents,
        )
        self.assertIn("Versão própria de componente e atualização independente são eixos diferentes", agents)
        self.assertIn("Versão própria de um componente e capacidade de atualizá-lo independentemente são eixos diferentes", nomenclature)


if __name__ == "__main__":
    unittest.main()
