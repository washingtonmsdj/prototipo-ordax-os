[CmdletBinding()]
param(
    [string]$ReleaseAgentPath = '',
    [string]$ExpectedCommit = '',
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

$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($ReleaseAgentPath)) {
    $ReleaseAgentPath = Join-Path $Root 'ordax-release-agent.exe'
}
if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
    $ReceiptPath = Join-Path $Root 'signed-handoff-verification.json'
}

$Agent = Get-RealFile $ReleaseAgentPath 'release acquisition agent'
$Manifest = Get-RealFile (Join-Path $Root 'release-manifest.json') 'release manifest'
$Envelope = Get-RealFile (Join-Path $Root 'release-envelope.json') 'signed release envelope'
$Trust = Get-RealFile (Join-Path $Root 'release-ed25519.json') 'canonical public trust'
$SystemImage = Get-RealFile (Join-Path $Root 'system.erofs') 'system.erofs'
$SurfaceRuntime = Get-RealFile (Join-Path $Root 'native-surface-runtime.erofs') 'native-surface-runtime.erofs'
$LocalAiRuntime = Get-RealFile (Join-Path $Root 'local-ai-runtime.erofs') 'local-ai-runtime.erofs'
$ReceiptPath = [IO.Path]::GetFullPath($ReceiptPath)

if (Test-Path -LiteralPath $ReceiptPath) {
    throw "Refusing to replace existing verification receipt: $ReceiptPath"
}

$verifyOutput = @(& $Agent verify-envelope --envelope $Envelope --trust $Trust 2>&1)
if ($LASTEXITCODE -ne 0) {
    $verifyOutput | ForEach-Object { Write-Host $_ }
    throw 'Signed release envelope verification failed.'
}
$verifyOutput | ForEach-Object { Write-Host $_ }

$manifestBytes = [IO.File]::ReadAllBytes($Manifest)
$manifest = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$manifest.'$schema' -cne 'prototype-ordax.release-manifest/4') {
    throw 'Signed handoff verification requires release-manifest/4.'
}
$sourceCommit = [string]$manifest.source_commit
if ($sourceCommit -cnotmatch '^[0-9a-f]{40}$') {
    throw 'Manifest source_commit is not exact lowercase 40-hex.'
}
if (-not [string]::IsNullOrWhiteSpace($ExpectedCommit) -and $ExpectedCommit -cne $sourceCommit) {
    throw "Manifest source commit mismatch: expected=$ExpectedCommit actual=$sourceCommit"
}

$envelope = Get-Content -LiteralPath $Envelope -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$envelope.'$schema' -cne 'prototype-ordax.release-envelope/1') {
    throw 'Unexpected release envelope schema.'
}
try {
    $signedPayload = [Convert]::FromBase64String([string]$envelope.payload)
} catch {
    throw 'Release envelope payload is not valid base64.'
}
if ($signedPayload.Length -ne $manifestBytes.Length) {
    throw 'Signed payload length differs from release-manifest.json.'
}
for ($i = 0; $i -lt $manifestBytes.Length; $i++) {
    if ($signedPayload[$i] -ne $manifestBytes[$i]) {
        throw 'Signed payload bytes differ from release-manifest.json.'
    }
}

$expected = [ordered]@{
    'system.erofs' = $SystemImage
    'native-surface-runtime.erofs' = $SurfaceRuntime
    'local-ai-runtime.erofs' = $LocalAiRuntime
}
$artifacts = @($manifest.artifacts)
if ($artifacts.Count -ne 3) {
    throw "release-manifest/4 must bind exactly three artifacts; found $($artifacts.Count)."
}
$artifactNames = @($artifacts | ForEach-Object { [string]$_.name })
if (($artifactNames -join ',') -cne 'system.erofs,native-surface-runtime.erofs,local-ai-runtime.erofs') {
    throw 'release-manifest/4 artifact order or identity is unexpected.'
}

$verifiedArtifacts = [ordered]@{}
foreach ($artifact in $artifacts) {
    $name = [string]$artifact.name
    if (-not $expected.Contains($name)) { throw "Unexpected signed artifact: $name" }
    $path = [string]$expected[$name]
    $item = Get-Item -LiteralPath $path -Force
    $signedSize = [Int64]$artifact.size
    if ($item.Length -ne $signedSize) {
        throw "Signed artifact size mismatch for ${name}: expected=$signedSize actual=$($item.Length)"
    }
    $signedHash = ([string]$artifact.sha256).ToLowerInvariant()
    if ($signedHash -cnotmatch '^[0-9a-f]{64}$') {
        throw "Signed artifact hash is malformed for $name."
    }
    $actualHash = Get-Sha256Lower $path
    if ($actualHash -cne $signedHash) {
        throw "Signed artifact SHA-256 mismatch for $name."
    }
    $verifiedArtifacts[$name] = [ordered]@{
        sha256 = $actualHash
        size = $item.Length
    }
}

$receiptDirectory = Split-Path -Parent $ReceiptPath
if (-not [string]::IsNullOrWhiteSpace($receiptDirectory) -and -not (Test-Path -LiteralPath $receiptDirectory)) {
    New-Item -ItemType Directory -Path $receiptDirectory | Out-Null
}

$receipt = [ordered]@{
    schema = 'prototype-ordax.portable-v4-signed-handoff-verification/1'
    source_commit = $sourceCommit
    release_manifest_sha256 = Get-Sha256Lower $Manifest
    release_envelope_sha256 = Get-Sha256Lower $Envelope
    canonical_trust_sha256 = Get-Sha256Lower $Trust
    artifacts = $verifiedArtifacts
    signature_verified_by_release_agent = $true
    signed_payload_matches_manifest_bytes = $true
    local_artifacts_match_signed_manifest = $true
    release_published = $false
    release_activated = $false
    portable_materialization_performed = $false
    physical_target_selected = $false
    physical_write_authorized_by_this_step = $false
    physical_write_performed = $false
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8

Write-Host ''
Write-Host 'PORTABLE_V4_SIGNED_HANDOFF_VERIFIED=YES'
Write-Host "SOURCE_COMMIT=$sourceCommit"
Write-Host "RELEASE_MANIFEST_SHA256=$($receipt.release_manifest_sha256)"
Write-Host "RELEASE_ENVELOPE_SHA256=$($receipt.release_envelope_sha256)"
Write-Host "CANONICAL_TRUST_SHA256=$($receipt.canonical_trust_sha256)"
Write-Host "VERIFICATION_RECEIPT=$ReceiptPath"
Write-Host 'SIGNED_PAYLOAD_MATCHES_MANIFEST_BYTES=YES'
Write-Host 'LOCAL_ARTIFACTS_MATCH_SIGNED_MANIFEST=YES'
Write-Host 'RELEASE_PUBLISHED=NO'
Write-Host 'RELEASE_ACTIVATED=NO'
Write-Host 'PORTABLE_MATERIALIZATION_PERFORMED=NO'
Write-Host 'PHYSICAL_TARGET_SELECTED=NO'
Write-Host 'PHYSICAL_WRITE_PERFORMED=NO'
Write-Host 'NEXT=review/publish the exact HTTPS artifacts, then run .\6-Materialize-Verify-PortableV4-Canonical.ps1'
