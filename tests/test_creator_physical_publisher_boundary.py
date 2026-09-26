import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSUMER_FLOW = ROOT / "docs/contracts/creator-consumer-flow.json"
PUBLISHER = ROOT / "tools/release-signing/windows/8-Sign-Publish-CreatorPhysical.ps1"
AUTHORIZATION = ROOT / "docs/contracts/physical-write-authorization.json"
PROMOTION = ROOT / "tools/creator/physical_promotion.py"


def _load_promotion_module():
    spec = importlib.util.spec_from_file_location("ordax_physical_promotion_publisher_test", PROMOTION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_consumer_creator_contract_is_portable_v2_not_legacy_seed_raw():
    data = json.loads(CONSUMER_FLOW.read_text(encoding="utf-8"))

    assert data["$schema"] == "prototype-ordax.creator-consumer-flow/2"
    assert data["publisher_boundary"]["physical_release_tag"] == "creator-physical"
    assert data["publisher_boundary"]["physical_release_envelope"] == "creator-physical-envelope.json"
    assert data["publisher_boundary"]["physical_release_purpose"] == "creator-portable-physical-windows-amd64"
    assert data["publisher_boundary"]["physical_release_recipe"] == "creator/physical/portable-windows/2"
    assert data["publisher_boundary"]["offline_canonical_signing_required_before_publication"] is True

    integrity = data["physical_candidate_integrity"]
    assert integrity["whole_disk_raw_image_required"] is False
    assert integrity["portable_artifact_count"] == 17
    assert integrity["portable_application_operation_count"] == 39
    assert "ordax-bootstrap-seed.raw" not in integrity["critical_files_bound_by_sha256_and_size"]
    assert set(integrity["critical_files_bound_by_sha256_and_size"]) == {
        "ordax-creator-physical-test.exe",
        "release-ed25519.json",
        "minimal-bootstrap.json",
        "portable-usb-v2.json",
        "creator-portable-media-plan.json",
        "physical-write-authorization.json",
        "provenance.json",
        "SHA256SUMS",
    }

    gate = data["physical_write_gate"]
    assert gate["requires_canonical_portable_application_plan"] is True
    assert gate["requires_exact_17_artifact_sources"] is True
    assert gate["internal_disk_write_allowed_in_mvp"] is False

    native = data["native_installation"]
    assert native["foundation_may_exist_in_source"] is True
    assert native["public_mvp_visible"] is False
    assert native["public_mvp_enabled"] is False
    assert native["internal_disk_destructive_apply_enabled"] is False


def test_physical_publisher_is_offline_keyed_first_publication_and_readback_gated():
    text = PUBLISHER.read_text(encoding="utf-8")

    required = (
        "PUBLISH_CREATOR_PHYSICAL_RELEASE",
        "python",
        "physical_promotion.py",
        "--require-ready",
        "ordax-physical-release-signing",
        "--private-key",
        "creator-physical-envelope.json",
        "creator-physical-manifest.json",
        "creator-portable-physical-windows-amd64",
        "creator/physical/portable-windows/2",
        "portable_artifact_count -ne 17",
        "portable_application_operation_count -ne 39",
        "physical_write_allowed -ne $true",
        "explicit_owner_authorization -ne $true",
        "gh",
        "release create",
        "release download",
        "--prerelease",
        "automatic replacement is forbidden",
        "PHYSICAL_TARGET_SELECTED=NO",
        "PHYSICAL_WRITE_PERFORMED=NO",
        "PUBLIC_STABLE_PROMOTED=NO",
    )
    for marker in required:
        assert marker in text

    assert "gh release delete" not in text
    assert "--clobber" not in text
    assert "release edit" not in text


def test_publisher_boundary_changes_do_not_invalidate_recorded_physical_authorization():
    module = _load_promotion_module()
    auth = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    context_sha, file_count = module.authorization_context_sha256(ROOT)

    assert auth["status"] == "authorized"
    assert auth["physical_write_allowed"] is True
    assert auth["explicit_owner_authorization"] is True
    assert context_sha == auth["authorization_context_sha256"]
    assert file_count == auth["authorization_context_file_count"]

    governed = {
        path.relative_to(ROOT).as_posix()
        for path in module.authorization_context_files(ROOT)
    }
    assert "docs/contracts/creator-consumer-flow.json" not in governed
    assert "tools/release-signing/windows/8-Sign-Publish-CreatorPhysical.ps1" not in governed
