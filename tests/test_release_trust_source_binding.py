from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INITIALIZER = (
    ROOT / "tools/release-signing/windows/Initialize-OrdaXReleaseTrust.ps1"
).read_text(encoding="utf-8")
FINALIZER = (
    ROOT / "tools/release-signing/windows/Complete-OrdaXReleaseTrust.ps1"
).read_text(encoding="utf-8")
TOOLKIT = (
    ROOT / ".github/workflows/windows-prototype-toolkit.yml"
).read_text(encoding="utf-8")
PREFLIGHT_WRAPPER = (
    ROOT / "tools/release-signing/windows/1-Verify-OrdaXTrustToolkit.cmd"
).read_text(encoding="utf-8")


def test_read_only_preflight_reuses_initializer_checks_before_key_generation():
    assert "[switch]$PreflightOnly" in INITIALIZER
    assert "if ($PreflightOnly)" in INITIALIZER
    assert "TOOLKIT_TRUST_PREFLIGHT=PASS" in INITIALIZER
    assert "CANONICAL_TRUST_CEREMONY_ELIGIBLE=YES" in INITIALIZER
    assert "PRIVATE_KEY_TOUCHED=NO" in INITIALIZER
    assert "FILESYSTEM_MUTATION=NO" in INITIALIZER
    assert INITIALIZER.index("if ($PreflightOnly)") < INITIALIZER.index("New-Item -ItemType Directory")
    assert '-PreflightOnly' in PREFLIGHT_WRAPPER
    assert '1-Verify-OrdaXTrustToolkit.cmd' in TOOLKIT
    assert '1-Verify-OrdaXTrustToolkit.cmd \\' in TOOLKIT


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


def test_recovery_refuses_source_identity_drift():
    assert "$ToolkitProvenancePath = Join-Path $ScriptRoot 'provenance.json'" in FINALIZER
    assert "$ToolkitProvenance.components.trust_recovery_finalizer.sha256" in FINALIZER
    assert "Trust recovery finalizer bytes do not match toolkit provenance." in FINALIZER
    assert "$InitialSourceCommit -ne $ToolkitSourceCommit" in FINALIZER
    assert "Initial trust ceremony source_commit does not match toolkit provenance." in FINALIZER
    assert "[string]$ProofManifest.source_commit -ne $ToolkitSourceCommit" in FINALIZER
    assert "[string]$ProofManifest.release_id -ne $ToolkitSourceCommit" in FINALIZER
    assert "Trust proof manifest source identity does not match toolkit provenance." in FINALIZER
    assert "TRUST_PROOF_SOURCE_IDENTITY_MATCH=YES" in FINALIZER
    assert "'trust_recovery_finalizer': {'name': 'Complete-OrdaXReleaseTrust.ps1', 'sha256': digest('Complete-OrdaXReleaseTrust.ps1')}" in TOOLKIT


def test_trust_ceremony_still_requires_local_private_custody():
    assert "The private key must be outside the downloaded toolkit/repository directory." in INITIALIZER
    assert "ready_to_pin_public_anchor = $false" in INITIALIZER
    assert "READY_TO_PIN_PUBLIC_ANCHOR=NO" in INITIALIZER
    assert "Assert-PrivateOutsideToolkit $PrimaryPrivateKeyPath" in FINALIZER
    assert "Assert-PrivateOutsideToolkit $RecoveredPrivateKeyPath" in FINALIZER


def test_canonical_trust_rejects_pr_and_manual_toolkits():
    assert "'source_repository': os.environ['GITHUB_REPOSITORY']" in TOOLKIT
    assert "'source_ref': os.environ['GITHUB_REF']" in TOOLKIT
    assert "'source_event': os.environ['GITHUB_EVENT_NAME']" in TOOLKIT
    assert "'canonical_trust_ceremony_eligible': (" in TOOLKIT
    assert "os.environ['GITHUB_EVENT_NAME'] == 'push'" in TOOLKIT
    assert "os.environ['GITHUB_REF'] == 'refs/heads/main'" in TOOLKIT
    for source in (INITIALIZER, FINALIZER):
        assert "$ToolkitProvenance.source_repository -ne 'washingtonmsdj/prototipo-ordax-os'" in source
        assert "$ToolkitProvenance.source_event -ne 'push'" in source
        assert "$ToolkitProvenance.source_ref -ne 'refs/heads/main'" in source
        assert "$ToolkitProvenance.canonical_trust_ceremony_eligible -ne $true" in source
        assert "Canonical trust ceremony requires a toolkit produced by a push of the canonical main branch." in source
