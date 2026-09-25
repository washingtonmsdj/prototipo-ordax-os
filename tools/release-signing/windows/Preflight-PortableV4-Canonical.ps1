[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SystemImagePath,
    [Parameter(Mandatory = $true)][string]$SurfaceRuntimePath,
    [Parameter(Mandatory = $true)][string]$LocalAiRuntimePath,
    [Parameter(Mandatory = $true)][string]$LocalAiSourceLockPath,
    [Parameter(Mandatory = $true)][string]$SystemReceiptPath,
    [Parameter(Mandatory = $true)][string]$SurfaceReceiptPath,
    [Parameter(Mandatory = $true)][string]$LocalAiReceiptPath,
    [Parameter(Mandatory = $true)][string]$SourceCommit,
    [Parameter(Mandatory = $true)][string]$SystemArtifactUrl,
    [Parameter(Mandatory = $true)][string]$SurfaceArtifactUrl,
    [Parameter(Mandatory = $true)][string]$LocalAiArtifactUrl,
    [string]$ManifestToolPath = '',
    [string]$SignerPath = '',
    [string]$ReleaseAgentPath = '',
    [string]$TrustPath = '',
    [string]$PrivateKeyPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RealFile {
    param([string]$Path, [string]$Label)
    $full = [IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "$Label was not found: $full"
    }
    $item = Get-Item -LiteralPath $full -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label may not be a reparse point or symlink: $full"
    }
    if ($item.Length -le 0) {
        throw "$Label is empty: $full"
    }
    return $full
}

function Get-StableHttpsUrl {
    param([string]$Value, [string]$Label)
    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri)) {
        throw "$Label must be an absolute URL."
    }
    if (
        $uri.Scheme -cne 'https' -or
        [string]::IsNullOrWhiteSpace($uri.Host) -or
        $uri.UserInfo -or
        -not [string]::IsNullOrEmpty($uri.Query) -or
        -not [string]::IsNullOrEmpty($uri.Fragment)
    ) {
        throw "$Label must be a stable public HTTPS URL without credentials, query or fragment."
    }
    return $uri.AbsoluteUri
}

function Get-JsonObject {
    param([string]$Path, [string]$Label)
    try {
        $value = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "$Label is not valid UTF-8 JSON."
    }
    if ($null -eq $value) {
        throw "$Label is empty JSON."
    }
    return $value
}

function Assert-OperatorReceipt {
    param(
        [string]$ReceiptPath,
        [string]$Kind,
        [string]$ExpectedCommit,
        [hashtable]$ExpectedFiles
    )

    $receipt = Get-JsonObject $ReceiptPath "$Kind operator receipt"
    if ([string]$receipt.'$schema' -cne 'prototype-ordax.canonical-v4-operator-artifact/1') {
        throw "$Kind operator receipt schema is invalid."
    }
    if ([string]$receipt.kind -cne $Kind) {
        throw "$Kind operator receipt kind does not match."
    }
    if ([string]$receipt.source_commit -cne $ExpectedCommit) {
        throw "$Kind operator receipt source commit does not match SourceCommit."
    }
    foreach ($field in @(
        'publication_performed',
        'signing_performed',
        'release_activated',
        'physical_target_selected',
        'physical_write_authorized',
        'physical_write_performed'
    )) {
        if ($receipt.$field -ne $false) {
            throw "$Kind operator receipt unexpectedly claims $field."
        }
    }

    $received = @{}
    foreach ($entry in @($receipt.files)) {
        $name = [string]$entry.name
        if ([string]::IsNullOrWhiteSpace($name) -or $received.ContainsKey($name)) {
            throw "$Kind operator receipt contains an invalid or duplicate file entry."
        }
        $received[$name] = $entry
    }
    if ($received.Count -ne $ExpectedFiles.Count) {
        throw "$Kind operator receipt file count does not match the expected set."
    }

    foreach ($name in $ExpectedFiles.Keys) {
        if (-not $received.ContainsKey($name)) {
            throw "$Kind operator receipt is missing $name."
        }
        $path = [string]$ExpectedFiles[$name]
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        $actualSize = (Get-Item -LiteralPath $path -Force).Length
        if ([string]$received[$name].sha256 -cne $actualHash) {
            throw "$Kind operator receipt SHA-256 does not match $name."
        }
        if ([int64]$received[$name].size -ne [int64]$actualSize) {
            throw "$Kind operator receipt size does not match $name."
        }
    }
}

if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') {
    throw 'SourceCommit must be an exact lowercase 40-hex Git commit.'
}

$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($ManifestToolPath)) {
    $ManifestToolPath = Join-Path $Root 'ordax-release-manifest.exe'
}
if ([string]::IsNullOrWhiteSpace($SignerPath)) {
    $SignerPath = Join-Path $Root 'ordax-release-signing.exe'
}
if ([string]::IsNullOrWhiteSpace($ReleaseAgentPath)) {
    $ReleaseAgentPath = Join-Path $Root 'ordax-release-agent.exe'
}
if ([string]::IsNullOrWhiteSpace($TrustPath)) {
    $TrustPath = Join-Path $Root 'release-ed25519.json'
}
if ([string]::IsNullOrWhiteSpace($PrivateKeyPath)) {
    if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        throw 'USERPROFILE is unavailable; provide -PrivateKeyPath explicitly.'
    }
    $PrivateKeyPath = Join-Path $env:USERPROFILE 'OrdaX-Private\release-signing\ordax-release-private.pem'
}

$SystemImagePath = Get-RealFile $SystemImagePath 'system.erofs'
$SurfaceRuntimePath = Get-RealFile $SurfaceRuntimePath 'native-surface-runtime.erofs'
$LocalAiRuntimePath = Get-RealFile $LocalAiRuntimePath 'local-ai-runtime.erofs'
$LocalAiSourceLockPath = Get-RealFile $LocalAiSourceLockPath 'local AI source lock'
$SystemReceiptPath = Get-RealFile $SystemReceiptPath 'system operator receipt'
$SurfaceReceiptPath = Get-RealFile $SurfaceReceiptPath 'Surface operator receipt'
$LocalAiReceiptPath = Get-RealFile $LocalAiReceiptPath 'Local AI operator receipt'
$ManifestToolPath = Get-RealFile $ManifestToolPath 'release manifest tool'
$SignerPath = Get-RealFile $SignerPath 'release signing tool'
$ReleaseAgentPath = Get-RealFile $ReleaseAgentPath 'release acquisition agent'
$TrustPath = Get-RealFile $TrustPath 'canonical public trust'
$PrivateKeyPath = Get-RealFile $PrivateKeyPath 'canonical private key'

if (
    $PrivateKeyPath.StartsWith($Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    $PrivateKeyPath.Equals($Root, [StringComparison]::OrdinalIgnoreCase)
) {
    throw 'The canonical private key must remain outside the public signing/tooling directory.'
}

Assert-OperatorReceipt $SystemReceiptPath 'system' $SourceCommit @{
    'system.erofs' = $SystemImagePath
}
Assert-OperatorReceipt $SurfaceReceiptPath 'surface' $SourceCommit @{
    'native-surface-runtime.erofs' = $SurfaceRuntimePath
}
Assert-OperatorReceipt $LocalAiReceiptPath 'local-ai' $SourceCommit @{
    'local-ai-runtime.erofs' = $LocalAiRuntimePath
    'source-lock.json' = $LocalAiSourceLockPath
}

$SystemArtifactUrl = Get-StableHttpsUrl $SystemArtifactUrl 'SystemArtifactUrl'
$SurfaceArtifactUrl = Get-StableHttpsUrl $SurfaceArtifactUrl 'SurfaceArtifactUrl'
$LocalAiArtifactUrl = Get-StableHttpsUrl $LocalAiArtifactUrl 'LocalAiArtifactUrl'

$trust = Get-JsonObject $TrustPath 'canonical public trust'
if ([string]$trust.'$schema' -cne 'prototype-ordax.release-trust/1') {
    throw 'Canonical public trust schema is invalid.'
}
if ([string]$trust.key_id -cne 'ordax-prototype-release-v1') {
    throw 'Canonical public trust key id is not ordax-prototype-release-v1.'
}
if ([string]::IsNullOrWhiteSpace([string]$trust.public_key_base64)) {
    throw 'Canonical public trust does not contain a public key.'
}

$lock = Get-JsonObject $LocalAiSourceLockPath 'local AI source lock'
if ([string]$lock.'$schema' -cne 'prototype-ordax.local-ai-source-lock/1') {
    throw 'Local AI source lock schema is invalid.'
}

foreach ($artifactPath in @($SystemImagePath, $SurfaceRuntimePath, $LocalAiRuntimePath)) {
    $item = Get-Item -LiteralPath $artifactPath -Force
    if ($item.Length -le 0) {
        throw "Canonical v4 artifact is empty: $artifactPath"
    }
}

Write-Host ''
Write-Host 'PORTABLE_V4_CANONICAL_OPERATOR_PREFLIGHT=PASS'
Write-Host "SOURCE_COMMIT=$SourceCommit"
Write-Host 'OPERATOR_RECEIPTS_MATCH_SOURCE_COMMIT=YES'
Write-Host 'OPERATOR_RECEIPT_BYTES_REVERIFIED=YES'
Write-Host "SYSTEM_ARTIFACT_URL=$SystemArtifactUrl"
Write-Host "SURFACE_ARTIFACT_URL=$SurfaceArtifactUrl"
Write-Host "LOCAL_AI_ARTIFACT_URL=$LocalAiArtifactUrl"
Write-Host "PRIVATE_KEY_PATH=$PrivateKeyPath"
Write-Host 'PRIVATE_KEY_CONTENT_READ_BY_PREFLIGHT=NO'
Write-Host 'SIGNATURE_CREATED=NO'
Write-Host 'RELEASE_PUBLISHED=NO'
Write-Host 'RELEASE_ACTIVATED=NO'
Write-Host 'PHYSICAL_TARGET_SELECTED=NO'
Write-Host 'PHYSICAL_WRITE_AUTHORIZED=NO'
Write-Host 'PHYSICAL_WRITE_PERFORMED=NO'
Write-Host 'NEXT=run 3-Prepare-PortableV4-SigningHandoff.ps1 with the same public inputs'
