import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "PLANO-00-ESTADO-ATUAL-E-PRIORIDADES.md"
PORTABLE_BOOTSTRAP = ROOT / "docs" / "contracts" / "portable-bootstrap-v2.json"
PORTABLE_MEDIA_PLAN = ROOT / "docs" / "contracts" / "creator-portable-media-plan.json"
QEMU_PROOF = ROOT / "docs" / "contracts" / "portable-v2-qemu-boot-proof.json"
UEFI_PROOF = ROOT / "docs" / "contracts" / "portable-v2-uefi-boot-proof.json"


class ExecutionRoadmapFreshnessTests(unittest.TestCase):
    def test_roadmap_tracks_structured_portable_state(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        bootstrap = json.loads(PORTABLE_BOOTSTRAP.read_text(encoding="utf-8"))
        media = json.loads(PORTABLE_MEDIA_PLAN.read_text(encoding="utf-8"))
        qemu = json.loads(QEMU_PROOF.read_text(encoding="utf-8"))
        uefi = json.loads(UEFI_PROOF.read_text(encoding="utf-8"))

        self.assertTrue(bootstrap["migration"]["portable_v2_pid1_integration_implemented"])
        self.assertTrue(media["physical_writer_v2_implemented"])
        self.assertFalse(media["public_mvp_default_enabled"])
        self.assertFalse(bootstrap["physical_boot_proven"])
        self.assertEqual(qemu["workflow"], ".github/workflows/portable-v2-qemu-boot-proof.yml")
        self.assertEqual(uefi["workflow"], ".github/workflows/portable-v2-qemu-boot-proof.yml")
        self.assertFalse(qemu["physical_boot_proven"])
        self.assertFalse(uefi["physical_usb_boot_proven"])

        self.assertIn("PORTABLE_V2_PID1_INTEGRATION=PASS_SOURCE", roadmap)
        self.assertIn("PORTABLE_QEMU_DIRECT_KERNEL_BOOT_BASELINE=PASS_CI_DISPOSABLE", roadmap)
        self.assertIn("PORTABLE_QEMU_UEFI_BOOT_BASELINE=PASS_CI_DISPOSABLE_OVMF_NON_SECURE_BOOT", roadmap)
        self.assertIn(
            "PORTABLE_RUNTIME_V3_CURRENT_MAIN_BASELINE_PROOF=PASS_CI_EVIDENCE_FILE",
            roadmap,
        )
        self.assertIn(
            "PORTABLE_V3_UPDATE_ACTIVATION=PASS_CI_DISPOSABLE_ONE_SHOT_FAILURE_FALLBACK",
            roadmap,
        )
        self.assertIn(
            "PORTABLE_V3_UPDATE_ROLLBACK=PASS_CI_DISPOSABLE_REJECTED_SHA_FALLBACK_PHYSICAL_PENDING",
            roadmap,
        )
        self.assertIn("PORTABLE_PHYSICAL_WRITER=PASS_TAGGED_INTERNAL", roadmap)
        self.assertIn("PORTABLE_PHYSICAL_USB_BOOT=NO", roadmap)
        self.assertIn("PUBLIC_PHYSICAL_APPLY=NO", roadmap)
        self.assertIn(
            "PORTABLE_COLD_HEALTH_PROOF_SCOPE=PHYSICAL_STABLE_MVP_REQUIRED_NO_SYNTHETIC_CI",
            roadmap,
        )

    def test_roadmap_tracks_structured_surface_smoke_finalization(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("`tour-template`", roadmap)
        self.assertIn("`finalize` fail-closed", roadmap)
        self.assertIn("12 itens do tour em PASS", roadmap)
        self.assertIn("runtime WebKit verificado Stable/MVP", roadmap)
        self.assertIn("layout físico de teclado configurado/aplicado", roadmap)
        self.assertIn("`final.json` tiver `FAIL=0`", roadmap)
        self.assertIn("comparação stale/editada", roadmap)

    def test_historical_blockers_cannot_return_as_current_priorities(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        for stale in (
            "Base inspecionada:",
            "A PR #357 concentra a fundação USB Stable/MVP",
            "9f1c9ec8f088a7d43fcb99402f4c65eb5cd07a81",
            "a correção deve habilitar o volume-ID FAT",
            "QEMU end-to-end proof is still pending",
        ):
            self.assertNotIn(stale, roadmap)

        self.assertIn("A consolidação USB-only da antiga PR #357 já foi integrada", roadmap)
        self.assertIn("A falha histórica `ORDAX-ESP partition not found`", roadmap)


if __name__ == "__main__":
    unittest.main()
