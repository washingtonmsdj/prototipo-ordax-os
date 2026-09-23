[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SystemImagePath,
    [Parameter(Mandatory = $true)][string]$SurfaceRuntimePath,
    [Parameter(Mandatory = $true)][string]$LocalAiRuntimePath,
    [Parameter(Mandatory = $true)][string]$LocalAiSourceLockPath,
    [Parameter(Mandatory = $true)][string]$SourceCommit,
    [Parameter(Mandatory = $true)][string]$SystemArtifactUrl,
    [Parameter(Mandatory = $true)][string]$SurfaceArtifactUrl,
    [Parameter(Mandatory = $true)][string]$LocalAiArtifactUrl,
    [string]$ManifestToolPath = '',
    [string]$SignerPath = '',
    [string]$ReleaseAgentPath = '',
    [string]$TrustPath = '',
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RealFile {
    param([string]$Path, [string]$Label)
    $full = [IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "$Label was not found: $full" }
    $item = Get-Item -LiteralPath $full -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label may not be a reparse point or symlink: $full" }
    return $full
}

function Get-HttpsUrl {
    param([string]$Value, [string]$Label)
    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri)) { throw "$Label must be an absolute URL." }
    if ($uri.Scheme -cne 'https' -or [string]::IsNullOrWhiteSpace($uri.Host) -or $uri.UserInfo) { throw "$Label must use HTTPS with no embedded credentials." }
    return $uri.AbsoluteUri
}

function New-EmptyRealDirectory {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    if (Test-Path -LiteralPath $full) {
        $item = Get-Item -LiteralPath $full -Force
        if (-not $item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) { throw "Output must be a real directory: $full" }
        if (@(Get-ChildItem -LiteralPath $full -Force).Count -ne 0) { throw "Output directory must be empty: $full" }
    } else {
        New-Item -ItemType Directory -Path $full | Out-Null
    }
    return $full
}

function Copy-VerifiedFile {
    param([string]$Source, [string]$Destination)
    Copy-Item -LiteralPath $Source -Destination $Destination
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Source).Hash.ToLowerInvariant()
    $destinationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash.ToLowerInvariant()
    if ($sourceHash -cne $destinationHash) { throw "Copied file hash mismatch: $Destination" }
    return $destinationHash
}

if ($SourceCommit -cnotmatch '^[0-9a-f]{40}$') { throw 'SourceCommit must be an exact lowercase 40-hex Git commit.' }

$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($ManifestToolPath)) { $ManifestToolPath = Join-Path $Root 'ordax-release-manifest.exe' }
if ([string]::IsNullOrWhiteSpace($SignerPath)) { $SignerPath = Join-Path $Root 'ordax-release-signing.exe' }
if ([string]::IsNullOrWhiteSpace($ReleaseAgentPath)) { $ReleaseAgentPath = Join-Path $Root 'ordax-release-agent.exe' }
if ([string]::IsNullOrWhiteSpace($TrustPath)) { $TrustPath = Join-Path $Root 'release-ed25519.json' }
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { $OutputDirectory = Join-Path $Root 'portable-v4-signing-handoff' }

$SystemImagePath = Get-RealFile $SystemImagePath 'system.erofs'
$SurfaceRuntimePath = Get-RealFile $SurfaceRuntimePath 'native-surface-runtime.erofs'
$LocalAiRuntimePath = Get-RealFile $LocalAiRuntimePath 'local-ai-runtime.erofs'
$LocalAiSourceLockPath = Get-RealFile $LocalAiSourceLockPath 'local AI source lock'
$ManifestToolPath = Get-RealFile $ManifestToolPath 'release manifest tool'
$SignerPath = Get-RealFile $SignerPath 'release signing tool'
$ReleaseAgentPath = Get-RealFile $ReleaseAgentPath 'release acquisition agent'
$TrustPath = Get-RealFile $TrustPath 'canonical public trust'
$SignScriptPath = Get-RealFile (Join-Path $Root '4-Sign-Initial-OrdaXRelease.ps1') 'canonical signing script'
$VerifyScriptPath = Get-RealFile (Join-Path $Root '5-Verify-PortableV4-SignedHandoff.ps1') 'post-sign verification script'

$SystemArtifactUrl = Get-HttpsUrl $SystemArtifactUrl 'SystemArtifactUrl'
$SurfaceArtifactUrl = Get-HttpsUrl $SurfaceArtifactUrl 'SurfaceArtifactUrl'
$LocalAiArtifactUrl = Get-HttpsUrl $LocalAiArtifactUrl 'LocalAiArtifactUrl'
$OutputDirectory = New-EmptyRealDirectory $OutputDirectory

$systemOut = Join-Path $OutputDirectory 'system.erofs'
$surfaceOut = Join-Path $OutputDirectory 'native-surface-runtime.erofs'
$aiOut = Join-Path $OutputDirectory 'local-ai-runtime.erofs'
$lockOut = Join-Path $OutputDirectory 'local-ai-source-lock.json'
$trustOut = Join-Path $OutputDirectory 'release-ed25519.json'
$signerOut = Join-Path $OutputDirectory 'ordax-release-signing.exe'
$agentOut = Join-Path $OutputDirectory 'ordax-release-agent.exe'
$signScriptOut = Join-Path $OutputDirectory '4-Sign-Initial-OrdaXRelease.ps1'
$verifyScriptOut = Join-Path $OutputDirectory '5-Verify-PortableV4-SignedHandoff.ps1'
$manifestOut = Join-Path $OutputDirectory 'release-manifest.json'

$systemSha = Copy-VerifiedFile $SystemImagePath $systemOut
$surfaceSha = Copy-VerifiedFile $SurfaceRuntimePath $surfaceOut
$aiSha = Copy-VerifiedFile $LocalAiRuntimePath $aiOut
$lockSha = Copy-VerifiedFile $LocalAiSourceLockPath $lockOut
$null = Copy-VerifiedFile $TrustPath $trustOut
$null = Copy-VerifiedFile $SignerPath $signerOut
$null = Copy-VerifiedFile $ReleaseAgentPath $agentOut
$null = Copy-VerifiedFile $SignScriptPath $signScriptOut
$null = Copy-VerifiedFile $VerifyScriptPath $verifyScriptOut

$manifestArgs = @(
    '--manifest-schema', '4',
    '--artifact', $systemOut,
    '--runtime-artifact', $surfaceOut,
    '--local-ai-artifact', $aiOut,
    '--local-ai-source-lock', $lockOut,
    '--source-commit', $SourceCommit,
    '--artifact-url', $SystemArtifactUrl,
    '--runtime-artifact-url', $SurfaceArtifactUrl,
    '--local-ai-artifact-url', $LocalAiArtifactUrl,
    '--out', $manifestOut
)
& $ManifestToolPath @manifestArgs | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Portable v4 release manifest generation failed.' }

$manifest = Get-Content -LiteralPath $manifestOut -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.'$schema' -cne 'prototype-ordax.release-manifest/4') { throw 'Generated manifest is not release-manifest/4.' }
if ([string]$manifest.source_commit -cne $SourceCommit) { throw 'Generated manifest source commit does not match the requested commit.' }
$artifactNames = @($manifest.artifacts | ForEach-Object { [string]$_.name })
if (($artifactNames -join ',') -cne 'system.erofs,native-surface-runtime.erofs,local-ai-runtime.erofs') { throw 'Generated v4 manifest artifact order/identity is unexpected.' }

$forbidden = @(Get-ChildItem -LiteralPath $OutputDirectory -Recurse -File | Where-Object { $_.Extension -in @('.pem', '.key', '.p12', '.pfx', '.dpapi') })
if ($forbidden.Count -ne 0) { throw 'Private signing material entered the public signing handoff.' }

$receipt = [ordered]@{
    schema = 'prototype-ordax.portable-v4-signing-handoff/1'
    source_commit = $SourceCommit
    release_manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestOut).Hash.ToLowerInvariant()
    canonical_trust_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $trustOut).Hash.ToLowerInvariant()
    artifacts = [ordered]@{
        'system.erofs' = $systemSha
        'native-surface-runtime.erofs' = $surfaceSha
        'local-ai-runtime.erofs' = $aiSha
        'local-ai-source-lock.json' = $lockSha
    }
    private_key_included = $false
    release_published = $false
    release_activated = $false
    physical_write_authorized = $false
}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'signing-handoff-receipt.json') -Encoding UTF8

Write-Host ''
Write-Host 'PORTABLE_V4_SIGNING_HANDOFF_READY=YES'
Write-Host "SOURCE_COMMIT=$SourceCommit"
Write-Host "HANDOFF_DIRECTORY=$OutputDirectory"
Write-Host "SYSTEM_EROFS_SHA256=$systemSha"
Write-Host "SURFACE_RUNTIME_EROFS_SHA256=$surfaceSha"
Write-Host "LOCAL_AI_RUNTIME_EROFS_SHA256=$aiSha"
Write-Host 'PRIVATE_KEY_INCLUDED=NO'
Write-Host 'RELEASE_PUBLISHED=NO'
Write-Host 'RELEASE_ACTIVATED=NO'
Write-Host 'PHYSICAL_WRITE_AUTHORIZED=NO'
