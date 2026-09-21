from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QEMU_WORKFLOW = ROOT / ".github" / "workflows" / "portable-v2-qemu-boot-proof.yml"


def test_qemu_heavy_trigger_scope_excludes_evidence_only_owners():
    text = QEMU_WORKFLOW.read_text(encoding="utf-8")

    # Runtime/boot implementation owners remain heavy-proof inputs.
    for required in (
        "bootstrap/initramfs/**",
        "bootstrap/portable-v2/**",
        "bootstrap/release-acquisition/**",
        ".github/workflows/portable-v2-qemu-boot-proof.yml",
    ):
        assert text.count(f"- '{required}'") == 2

    # Updating proof status/evidence regressions does not change boot bytes.
    for excluded in (
        "docs/contracts/portable-v3-one-shot-qemu-proof-spec.json",
        "tests/test_portable_v3_one_shot_qemu_proof.py",
    ):
        assert excluded not in text
