[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$EnvelopeUrl,
    [Parameter(Mandatory = $true)][string]$ExpectedCommit,
    [string]$ReleaseAgentPath = '',
    [string]$TrustPath = '',
    [string]$MaterializationRoot = '',
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

function Get-PublicHttpsUrl {
    param([string]$Value)
    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri)) {
        throw 'EnvelopeUrl must be an absolute URL.'
    }
    if ($uri.Scheme -cne 'https' -or [string]::IsNullOrWhiteSpace($uri.Host) -or $uri.UserInfo) {
        throw 'EnvelopeUrl must use HTTPS with no embedded credentials.'
    }
    if (-not [string]::IsNullOrEmpty($uri.Query) -or -not [string]::IsNullOrEmpty($uri.Fragment)) {
        throw 'EnvelopeUrl must be a stable public HTTPS URL without query or fragment.'
    }
    return $uri.AbsoluteUri
}

function New-EmptyRealDirectory {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    if (Test-Path -LiteralPath $full) {
        $item = Get-Item -LiteralPath $full -Force
        if (-not $item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw "Materialization root must be a real directory: $full"
        }
        if (@(Get-ChildItem -LiteralPath $full -Force).Count -ne 0) {
            throw "Materialization root must be empty: $full"
        }
    } else {
        New-Item -ItemType Directory -Path $full | Out-Null
    }
    return $full
}

function Get-Sha256Lower {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ($ExpectedCommit -cnotmatch '^[0-9a-f]{40}$') {
    throw 'ExpectedCommit must be an exact lowercase 40-hex Git commit.'
}
if ([string]::IsNullOrWhiteSpace($ReleaseAgentPath)) {
    $ReleaseAgentPath = Join-Path $Root 'ordax-release-agent.exe'
}
if ([string]::IsNullOrWhiteSpace($TrustPath)) {
    $TrustPath = Join-Path $Root 'release-ed25519.json'
}
if ([string]::IsNullOrWhiteSpace($MaterializationRoot)) {
    $MaterializationRoot = Join-Path $Root 'portable-v4-canonical-materialized'
}
if ([string]::IsNullOrWhiteSpace($ReceiptPath)) {
    $ReceiptPath = Join-Path $Root 'canonical-materialization-verification.json'
}

$Agent = Get-RealFile $ReleaseAgentPath 'release acquisition agent'
$Trust = Get-RealFile $TrustPath 'canonical public trust'
$EnvelopeUrl = Get-PublicHttpsUrl $EnvelopeUrl
$MaterializationRoot = New-EmptyRealDirectory $MaterializationRoot
$ReceiptPath = [IO.Path]::GetFullPath($ReceiptPath)

if (Test-Path -LiteralPath $ReceiptPath) {
    throw "Refusing to replace existing materialization receipt: $ReceiptPath"
}
if ($ReceiptPath.StartsWith($MaterializationRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ReceiptPath must remain outside the materialization root.'
}

& $Agent materialize-portable-v4 `
    --envelope-url $EnvelopeUrl `
    --trust $Trust `
    --expected-commit $ExpectedCommit `
    --root $MaterializationRoot
if ($LASTEXITCODE -ne 0) {
    throw 'Canonical Portable v4 materialization failed.'
}

& $Agent verify-portable-v4-exact `
    --trust $Trust `
    --expected-commit $ExpectedCommit `
    --root $MaterializationRoot
if ($LASTEXITCODE -ne 0) {
    throw 'Canonical Portable v4 exact offline verification failed.'
}

foreach ($forbiddenRelative in @('current', 'known-good', 'candidate', 'activation-transaction.json')) {
    $forbiddenPath = Join-Path $MaterializationRoot $forbiddenRelative
    if (Test-Path -LiteralPath $forbiddenPath) {
        throw "Materialization unexpectedly created activation state: $forbiddenRelative"
    }
}

$ReleaseDirectory = Join-Path (Join-Path $MaterializationRoot 'releases') $ExpectedCommit
$SystemImage = Get-RealFile (Join-Path $ReleaseDirectory 'system.erofs') 'materialized system.erofs'
$Manifest = Get-RealFile (Join-Path $ReleaseDirectory 'release-manifest.json') 'materialized release manifest'
$Envelope = Get-RealFile (Join-Path $ReleaseDirectory 'release-envelope.json') 'materialized release envelope'
$SurfaceRef = Get-RealFile (Join-Path $ReleaseDirectory 'surface-runtime.sha256') 'surface runtime reference'
$LocalAiRef = Get-RealFile (Join-Path $ReleaseDirectory 'local-ai-runtime.sha256') 'local AI runtime reference'

$surfaceSha = (Get-Content -LiteralPath $SurfaceRef -Raw -Encoding UTF8).Trim()
$localAiSha = (Get-Content -LiteralPath $LocalAiRef -Raw -Encoding UTF8).Trim()
foreach ($entry in @(
    @{ Label = 'surface runtime SHA-256'; Value = $surfaceSha },
    @{ Label = 'local AI runtime SHA-256'; Value = $localAiSha }
)) {
    if ([string]$entry.Value -cnotmatch '^[0-9a-f]{64}$') {
        throw "$($entry.Label) reference is malformed."
    }
}

$SurfaceRuntime = Get-RealFile (
    Join-Path $MaterializationRoot "runtimes/sha256/$surfaceSha/native-surface-runtime.erofs"
) 'content-addressed Surface runtime'
$LocalAiRuntime = Get-RealFile (
    Join-Path $MaterializationRoot "ai-runtimes/sha256/$localAiSha/local-ai-runtime.erofs"
) 'content-addressed local AI runtime'

$manifestDocument = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$manifestDocument.'$schema' -cne 'prototype-ordax.release-manifest/4') {
    throw 'Materialized manifest is not release-manifest/4.'
}
if ([string]$manifestDocument.source_commit -cne $ExpectedCommit) {
    throw 'Materialized manifest source commit differs from ExpectedCommit.'
}

$receiptDirectory = Split-Path -Parent $ReceiptPath
if (-not [string]::IsNullOrWhiteSpace($receiptDirectory) -and -not (Test-Path -LiteralPath $receiptDirectory)) {
    New-Item -ItemType Directory -Path $receiptDirectory | Out-Null
}

$receipt = [ordered]@{
    schema = 'prototype-ordax.portable-v4-canonical-materialization-verification/1'
    source_commit = $ExpectedCommit
    canonical_envelope_url = $EnvelopeUrl
    canonical_trust_sha256 = Get-Sha256Lower $Trust
    release_manifest_sha256 = Get-Sha256Lower $Manifest
    release_envelope_sha256 = Get-Sha256Lower $Envelope
    artifacts = [ordered]@{
        'system.erofs' = Get-Sha256Lower $SystemImage
        'native-surface-runtime.erofs' = Get-Sha256Lower $SurfaceRuntime
        'local-ai-runtime.erofs' = Get-Sha256Lower $LocalAiRuntime
    }
    release_agent_materialize_portable_v4 = $true
    release_agent_verify_portable_v4_exact = $true
    current_pointer_created = $false
    known_good_pointer_created = $false
    candidate_created = $false
    activation_transaction_created = $false
    release_activated = $false
    physical_target_selected = $false
    physical_write_authorized_by_this_step = $false
    physical_write_performed = $false
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8

Write-Host ''
Write-Host 'PORTABLE_V4_CANONICAL_MATERIALIZATION_VERIFIED=YES'
Write-Host "SOURCE_COMMIT=$ExpectedCommit"
Write-Host "MATERIALIZATION_ROOT=$MaterializationRoot"
Write-Host "VERIFICATION_RECEIPT=$ReceiptPath"
Write-Host "SYSTEM_EROFS_SHA256=$($receipt.artifacts.'system.erofs')"
Write-Host "SURFACE_RUNTIME_EROFS_SHA256=$($receipt.artifacts.'native-surface-runtime.erofs')"
Write-Host "LOCAL_AI_RUNTIME_EROFS_SHA256=$($receipt.artifacts.'local-ai-runtime.erofs')"
Write-Host 'RELEASE_ACTIVATED=NO'
Write-Host 'PHYSICAL_TARGET_SELECTED=NO'
Write-Host 'PHYSICAL_WRITE_PERFORMED=NO'
