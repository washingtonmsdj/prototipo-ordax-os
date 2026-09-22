from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROADMAP = (ROOT / "PLANO-00-ESTADO-ATUAL-E-PRIORIDADES.md").read_text(encoding="utf-8")
SYSTEM_UI = (ROOT / "system/surface/ui/system-overview-controls.mjs").read_text(encoding="utf-8")
DIAGNOSTICS_UI = (ROOT / "system/surface/ui/system-diagnostics-review.mjs").read_text(encoding="utf-8")
FILE_SPACE = (ROOT / "system/contracts/file-space.mjs").read_text(encoding="utf-8")
PROMOTION = (ROOT / "docs/PROMOTION-GATES.md").read_text(encoding="utf-8")


def assignments(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Z0-9_]+)=([^\s]+)", line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


class CurrentExecutionRoadmapTests(unittest.TestCase):
    def test_overlay_declares_source_and_canonical_docs_as_higher_authority(self):
        self.assertIn("contratos e código estruturado do commit atual", ROADMAP)
        self.assertIn("`docs/CURRENT-STATE.md` e `docs/PROMOTION-GATES.md`", ROADMAP)
        self.assertIn("inventários e prioridades históricas dos planos longos", ROADMAP)
        self.assertIn("Drift documental não autoriza duplicar", ROADMAP)

    def test_system_inventory_matches_canonical_sections_and_history_wiring(self):
        for section in ("overview", "updates", "storage", "diagnostics", "about"):
            self.assertIn(f'id: "{section}"', SYSTEM_UI)
        self.assertIn('from "../../contracts/update-history.mjs"', SYSTEM_UI)
        self.assertIn('from "./system-diagnostics-review.mjs"', SYSTEM_UI)

        for label in ("Visão geral", "Atualizações", "Armazenamento", "Diagnóstico", "Sobre"):
            self.assertIn(f"**{label}**", ROADMAP)
        self.assertIn("O histórico de atualização já possui porta", ROADMAP)

    def test_diagnostic_review_is_not_listed_as_a_missing_greenfield_feature(self):
        for method in (
            '"prepare"',
            '"copyPreparedSummary"',
            '"exportPrepared"',
        ):
            self.assertIn(method, DIAGNOSTICS_UI)
        self.assertIn("copiar resumo sanitizado", ROADMAP)
        self.assertIn("salvar/exportar a revisão preparada", ROADMAP)
        self.assertIn("estão obsoletos nesse ponto", ROADMAP)

    def test_file_space_version_is_current_in_overlay(self):
        self.assertIn("ordax.file-space/11", FILE_SPACE)
        self.assertIn("`ordax.file-space/11`", ROADMAP)

    def test_overlay_preserves_fail_closed_promotion_state(self):
        promotion = assignments(PROMOTION)
        expected = {
            "MVP_SURFACE_SMOKE_HARNESS": "PASS_SOURCE",
            "MVP_SURFACE_SMOKE_PHYSICAL": "PENDING",
            "CANONICAL_STABLE_GRAPHICAL_MODE": "PENDING",
            "CANONICAL_RELEASE_TRUST": "PASS_CANONICAL_PUBLIC_ANCHOR_PINNED",
            "PUBLIC_PHYSICAL_APPLY": "NO",
        }
        for key, value in expected.items():
            self.assertEqual(promotion.get(key), value)
            self.assertIn(f"{key}={value}", ROADMAP)

    def test_overlay_does_not_convert_development_or_qemu_evidence_into_physical_pass(self):
        self.assertIn("não substituem", ROADMAP)
        self.assertIn("não converte execução pendente em PASS físico", ROADMAP)
        self.assertNotIn("MVP_SURFACE_SMOKE_PHYSICAL=PASS", ROADMAP)
        self.assertNotIn("CANONICAL_STABLE_GRAPHICAL_MODE=PASS", ROADMAP)
        self.assertIn("CANONICAL_RELEASE_TRUST=PASS_CANONICAL_PUBLIC_ANCHOR_PINNED", ROADMAP)


if __name__ == "__main__":
    unittest.main()
