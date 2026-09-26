[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExpectedCommit,
    [string]$SignedHandoffReceiptPath = '',
    [string]$MaterializationReceiptPath = '',
    [string]$TrustPath = '',
    [string]$ReceiptPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RealFile {
    param([string]$Path, [string]$Label)
    $full = [IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "$Label was not found: $full" }
    $item = Get-Item -LiteralPath $full -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label may not be a reparse point or symlink: $full"
    }
    return $full
}

function Get-Sha256Lower {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-Json {
    param([string]$Path, [string]$Label)
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "$Label is not valid JSON."
    }
}

function Require-LowerSha256 {
    param([string]$Value, [string]$Label)
    if ($Value -cnotmatch '^[0-9a-f]{64}$') { throw "$Label must be exact lowercase SHA-256." }
    return $Value
}

function Require-False {
    param($Value, [string]$Label)
    if ($Value -isnot [bool] -or $Value -ne $false) { throw "$Label must be JSON boolean false." }
}

function Require-True {
    param($Value, [string]$Label)
    if ($Value -isnot [bool] -or $Value -ne $true) { throw "$Label must be JSON boolean true." }
}

$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ($ExpectedCommit -cnotmatch '^[0-9a-f]{40}$') {
    throw 'ExpectedCommit must be an exact lowercase 40-hex Git commit.'
}
if ([string]::IsNullOrWhiteSpace($SignedHandoffReceiptPath)) {
    $SignedHandoffReceiptPath = Join-Path $Root 'signed-handoff-verification.json'
}
if ([string]::IsNullOrWhiteSpace($MaterializationReceiptPath)) {
    $MaterializationReceiptPath = Join-Path $Root 'canonical-materialization-verification.json'
}
if ([string]::IsNullOrWhiteSpace($TrustPath)) {
    $TrustPath = Join-Path $Root 'release-ed25519.json'
}
if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
    $ReceiptPath = Join-Path $Root 'canonical-v4-release-proof.json'
}

$SignedReceiptPath = Get-RealFile $SignedHandoffReceiptPath 'signed handoff verification receipt'
$MaterialReceiptPath = Get-RealFile $MaterializationReceiptPath 'canonical materialization receipt'
$Trust = Get-RealFile $TrustPath 'canonical public trust'
$ReceiptPath = [IO.Path]::GetFullPath($ReceiptPath)
if (Test-Path -LiteralPath $ReceiptPath) {
    throw "Refusing to replace existing canonical proof receipt: $ReceiptPath"
}
if ($ReceiptPath -ceq $SignedReceiptPath -or $ReceiptPath -ceq $MaterialReceiptPath -or $ReceiptPath -ceq $Trust) {
    throw 'Canonical proof receipt must be a distinct output file.'
}

$signed = Get-Json $SignedReceiptPath 'signed handoff verification receipt'
$materialized = Get-Json $MaterialReceiptPath 'canonical materialization receipt'

if ([string]$signed.schema -cne 'prototype-ordax.portable-v4-signed-handoff-verification/1') {
    throw 'Signed handoff receipt schema is invalid.'
}
if ([string]$materialized.schema -cne 'prototype-ordax.portable-v4-canonical-materialization-verification/1') {
    throw 'Canonical materialization receipt schema is invalid.'
}
if ([string]$signed.source_commit -cne $ExpectedCommit -or [string]$materialized.source_commit -cne $ExpectedCommit) {
    throw 'Canonical v4 receipts do not bind the expected source commit.'
}

$canonicalEnvelopeUrl = [string]$materialized.canonical_envelope_url
$canonicalEnvelopeUri = $null
if (-not [Uri]::TryCreate($canonicalEnvelopeUrl, [UriKind]::Absolute, [ref]$canonicalEnvelopeUri) -or
    $canonicalEnvelopeUri.Scheme -cne 'https' -or
    [string]::IsNullOrWhiteSpace($canonicalEnvelopeUri.Host) -or
    $canonicalEnvelopeUri.UserInfo -or
    -not [string]::IsNullOrEmpty($canonicalEnvelopeUri.Query) -or
    -not [string]::IsNullOrEmpty($canonicalEnvelopeUri.Fragment)) {
    throw 'Canonical materialization receipt envelope URL is not a stable public HTTPS URL.'
}

$actualTrustSha = Get-Sha256Lower $Trust
$signedTrustSha = Require-LowerSha256 ([string]$signed.canonical_trust_sha256) 'signed receipt canonical trust'
$materialTrustSha = Require-LowerSha256 ([string]$materialized.canonical_trust_sha256) 'materialization receipt canonical trust'
if ($signedTrustSha -cne $actualTrustSha -or $materialTrustSha -cne $actualTrustSha) {
    throw 'Canonical v4 receipts do not bind the exact local canonical public trust.'
}

$signedManifestSha = Require-LowerSha256 ([string]$signed.release_manifest_sha256) 'signed receipt manifest'
$materialManifestSha = Require-LowerSha256 ([string]$materialized.release_manifest_sha256) 'materialization receipt manifest'
if ($signedManifestSha -cne $materialManifestSha) {
    throw 'Signed and materialized manifest SHA-256 differ.'
}
$signedEnvelopeSha = Require-LowerSha256 ([string]$signed.release_envelope_sha256) 'signed receipt envelope'
$materialEnvelopeSha = Require-LowerSha256 ([string]$materialized.release_envelope_sha256) 'materialization receipt envelope'
if ($signedEnvelopeSha -cne $materialEnvelopeSha) {
    throw 'Signed and materialized envelope SHA-256 differ.'
}

Require-True $signed.signature_verified_by_release_agent 'signed receipt signature_verified_by_release_agent'
Require-True $signed.signed_payload_matches_manifest_bytes 'signed receipt signed_payload_matches_manifest_bytes'
Require-True $signed.local_artifacts_match_signed_manifest 'signed receipt local_artifacts_match_signed_manifest'
Require-False $signed.release_published 'signed receipt release_published'
Require-False $signed.release_activated 'signed receipt release_activated'
Require-False $signed.portable_materialization_performed 'signed receipt portable_materialization_performed'
Require-False $signed.physical_target_selected 'signed receipt physical_target_selected'
Require-False $signed.physical_write_authorized_by_this_step 'signed receipt physical_write_authorized_by_this_step'
Require-False $signed.physical_write_performed 'signed receipt physical_write_performed'

Require-True $materialized.release_agent_materialize_portable_v4 'materialization receipt release_agent_materialize_portable_v4'
Require-True $materialized.release_agent_verify_portable_v4_exact 'materialization receipt release_agent_verify_portable_v4_exact'
Require-False $materialized.current_pointer_created 'materialization receipt current_pointer_created'
Require-False $materialized.known_good_pointer_created 'materialization receipt known_good_pointer_created'
Require-False $materialized.candidate_created 'materialization receipt candidate_created'
Require-False $materialized.activation_transaction_created 'materialization receipt activation_transaction_created'
Require-False $materialized.release_activated 'materialization receipt release_activated'
Require-False $materialized.physical_target_selected 'materialization receipt physical_target_selected'
Require-False $materialized.physical_write_authorized_by_this_step 'materialization receipt physical_write_authorized_by_this_step'
Require-False $materialized.physical_write_performed 'materialization receipt physical_write_performed'

$artifactProof = [ordered]@{}
foreach ($name in @('system.erofs', 'native-surface-runtime.erofs', 'local-ai-runtime.erofs')) {
    $signedProperty = $signed.artifacts.PSObject.Properties[$name]
    $materialProperty = $materialized.artifacts.PSObject.Properties[$name]
    if ($null -eq $signedProperty -or $null -eq $materialProperty) {
        throw "Canonical v4 receipt is missing artifact: $name"
    }
    $signedArtifact = $signedProperty.Value
    $signedSha = Require-LowerSha256 ([string]$signedArtifact.sha256) "signed receipt artifact $name"
    $materialSha = Require-LowerSha256 ([string]$materialProperty.Value) "materialization receipt artifact $name"
    if ($signedSha -cne $materialSha) {
        throw "Signed and materialized artifact SHA-256 differ for $name."
    }
    if ($signedArtifact.size -isnot [int] -and $signedArtifact.size -isnot [long]) {
        throw "Signed receipt artifact size must be a JSON integer for $name."
    }
    $size = [Int64]$signedArtifact.size
    if ($size -le 0) { throw "Signed receipt artifact size is invalid for $name." }
    $artifactProof[$name] = [ordered]@{
        sha256 = $signedSha
        size = $size
    }
}

$receiptDirectory = Split-Path -Parent $ReceiptPath
if (-not [string]::IsNullOrWhiteSpace($receiptDirectory) -and -not (Test-Path -LiteralPath $receiptDirectory)) {
    New-Item -ItemType Directory -Path $receiptDirectory | Out-Null
}

$receipt = [ordered]@{
    schema = 'prototype-ordax.portable-v4-canonical-release-proof/1'
    source_commit = $ExpectedCommit
    canonical_envelope_url = $canonicalEnvelopeUrl
    canonical_trust_sha256 = $actualTrustSha
    release_manifest_sha256 = $signedManifestSha
    release_envelope_sha256 = $signedEnvelopeSha
    artifacts = $artifactProof
    signed_handoff_receipt_sha256 = Get-Sha256Lower $SignedReceiptPath
    canonical_materialization_receipt_sha256 = Get-Sha256Lower $MaterialReceiptPath
    signed_handoff_verified = $true
    canonical_materialization_verified = $true
    release_activated = $false
    physical_target_selected = $false
    physical_write_authorized = $false
    physical_write_performed = $false
}
# Windows PowerShell 5.1 adds a BOM with Set-Content -Encoding UTF8. The
# host-neutral binder validates and hashes these exact bytes without rewriting.
[IO.File]::WriteAllText(
    $ReceiptPath,
    ($receipt | ConvertTo-Json -Depth 6) + [Environment]::NewLine,
    [Text.UTF8Encoding]::new($false)
)

Write-Host ''
Write-Host 'PORTABLE_V4_CANONICAL_RELEASE_PROOF=PASS'
Write-Host "SOURCE_COMMIT=$ExpectedCommit"
Write-Host "CANONICAL_ENVELOPE_URL=$canonicalEnvelopeUrl"
Write-Host "CANONICAL_TRUST_SHA256=$actualTrustSha"
Write-Host "RELEASE_MANIFEST_SHA256=$signedManifestSha"
Write-Host "RELEASE_ENVELOPE_SHA256=$signedEnvelopeSha"
Write-Host "PROOF_RECEIPT=$ReceiptPath"
Write-Host 'SIGNED_HANDOFF_VERIFIED=YES'
Write-Host 'CANONICAL_MATERIALIZATION_VERIFIED=YES'
Write-Host 'RELEASE_ACTIVATED=NO'
Write-Host 'PHYSICAL_TARGET_SELECTED=NO'
Write-Host 'PHYSICAL_WRITE_AUTHORIZED=NO'
Write-Host 'PHYSICAL_WRITE_PERFORMED=NO'
Write-Host 'NEXT=review this proof, then request fresh v4 physical-media authorization separately'
