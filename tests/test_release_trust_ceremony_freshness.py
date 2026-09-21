from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CEREMONY = (ROOT / "docs/RELEASE-TRUST-CEREMONY.md").read_text(encoding="utf-8")
PROMOTER = (ROOT / "tools/release-signing/promote_public_trust.py").read_text(encoding="utf-8")


def test_public_trust_promotion_keeps_physical_write_fail_closed():
    section = CEREMONY.split("## Public-anchor promotion", 1)[1].split("## CI signing", 1)[0]
    assert "MINIMAL_BOOTSTRAP_ALL_ARTIFACTS_RESOLVED=YES" in section
    assert section.count("PHYSICAL_AUTHORIZATION_ELIGIBLE=YES") == 2
    assert "PHYSICAL_AUTHORIZATION_ELIGIBLE=NO" not in section
    assert "PHYSICAL_WRITE_ALLOWED=NO" in section
    assert "It is not an authorization to write physical media." in section


def test_ceremony_matches_promoter_gate_semantics():
    assert 'gates["physical_authorization_eligible"] = True' in PROMOTER
    assert '"physical_write_allowed": False' in PROMOTER


def test_ceremony_requires_one_provenance_bound_windows_toolkit():
    required = CEREMONY.split("## Required local ceremony", 1)[1].split("## Independent public derivation", 1)[0]
    assert "2-Initialize-OrdaXTrust.cmd" in required
    assert "prototype-ordax.windows-prototype-toolkit/2" in required
    assert "source_commit" in required
    assert "40 lowercase hexadecimal characters" in required
    assert "SHA-256 of `ordax-release-signing.exe` matches the toolkit provenance" in required
    assert "SHA-256 of `Initialize-OrdaXReleaseTrust.ps1` matches the toolkit provenance" in required
    assert "do not mix files from different toolkit runs" in required
    assert "placeholder commit" in required

def test_public_trust_promotion_uses_single_zip_for_check_and_apply():
    section = CEREMONY.split("## Public-anchor promotion", 1)[1].split("## CI signing", 1)[0]
    assert section.count("--promotion-zip") == 2
    assert "--promotion-dir" not in section
    assert "OrdaX-Public-Trust-Handoff.zip" in section
    assert "manual extraction is not required" in section


def test_rotation_docs_match_implemented_but_not_activated_boundary():
    section = CEREMONY.split("## Rotation", 1)[1].split("Current fail-closed state", 1)[0]
    assert "signed trust-transition protocol v1 is now implemented and CI-proven" in section
    assert "Stateful device activation" in section
    assert "production rotation is not yet complete" in section

