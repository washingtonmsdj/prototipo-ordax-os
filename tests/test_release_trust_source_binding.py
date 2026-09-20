from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INITIALIZER = (
    ROOT / "tools/release-signing/windows/Initialize-OrdaXReleaseTrust.ps1"
).read_text(encoding="utf-8")
TOOLKIT = (
    ROOT / ".github/workflows/windows-prototype-toolkit.yml"
).read_text(encoding="utf-8")


def test_trust_ceremony_binds_proof_to_toolkit_source_commit():
    assert "$ToolkitProvenancePath = Join-Path $ScriptRoot 'provenance.json'" in INITIALIZER
    assert "prototype-ordax.windows-prototype-toolkit/2" in INITIALIZER
    assert "$ToolkitSourceCommit -notmatch '^[0-9a-f]{40}$'" in INITIALIZER
    assert "$ProofCommit = $ToolkitSourceCommit" in INITIALIZER
    assert "source_commit = $ToolkitSourceCommit" in INITIALIZER
    assert 'Write-Host "SOURCE_COMMIT=$ToolkitSourceCommit"' in INITIALIZER
    assert "'source_commit': os.environ['GITHUB_SHA']" in TOOLKIT
    assert "(root / 'provenance.json').write_text" in TOOLKIT


def test_trust_ceremony_verifies_toolkit_components_before_key_generation():
    assert "$ToolkitProvenance.components.release_signer.sha256" in INITIALIZER
    assert "$ToolkitProvenance.components.trust_initializer.sha256" in INITIALIZER
    assert "Get-FileHash -Algorithm SHA256 -LiteralPath $Signer" in INITIALIZER
    assert "Get-FileHash -Algorithm SHA256 -LiteralPath $ScriptPath" in INITIALIZER
    assert "Release signer bytes do not match toolkit provenance." in INITIALIZER
    assert "Trust initializer bytes do not match toolkit provenance." in INITIALIZER
    assert "TOOLKIT_COMPONENT_HASHES_VERIFIED=YES" in INITIALIZER
    assert "'release_signer': {'name': 'ordax-release-signing.exe', 'sha256': digest('ordax-release-signing.exe')}" in TOOLKIT
    assert "'trust_initializer': {'name': 'Initialize-OrdaXReleaseTrust.ps1', 'sha256': digest('Initialize-OrdaXReleaseTrust.ps1')}" in TOOLKIT


def test_trust_ceremony_still_requires_local_private_custody():
    assert "The private key must be outside the downloaded toolkit/repository directory." in INITIALIZER
    assert "ready_to_pin_public_anchor = $false" in INITIALIZER
    assert "READY_TO_PIN_PUBLIC_ANCHOR=NO" in INITIALIZER
