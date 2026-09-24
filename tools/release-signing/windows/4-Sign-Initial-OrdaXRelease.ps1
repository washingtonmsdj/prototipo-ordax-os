[CmdletBinding()]
param(
    [string]$PrivateKeyPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$KeyId = 'ordax-prototype-release-v1'
$Root = [IO.Path]::GetFullPath($PSScriptRoot)
if ([string]::IsNullOrWhiteSpace($PrivateKeyPath)) {
    if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        throw 'USERPROFILE is unavailable; provide -PrivateKeyPath explicitly.'
    }
    # Keep this identical to Initialize-OrdaXReleaseTrust.ps1 and the Creator
    # publisher finalizer. LOCALAPPDATA can traverse Windows reparse/junction
    # aliases that the release signer intentionally refuses for private keys.
    $PrivateKeyPath = Join-Path $env:USERPROFILE 'OrdaX-Private\release-signing\ordax-release-private.pem'
}
$PrivateKeyPath = [IO.Path]::GetFullPath($PrivateKeyPath)
$Signer = Join-Path $Root 'ordax-release-signing.exe'
$Manifest = Join-Path $Root 'release-manifest.json'
$Trust = Join-Path $Root 'release-ed25519.json'
$Envelope = Join-Path $Root 'release-envelope.json'

foreach ($path in @($Signer, $Manifest, $Trust, $PrivateKeyPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file is missing: $path"
    }
    $item = Get-Item -LiteralPath $path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Required file may not be a reparse point or symlink: $path"
    }
}
if (Test-Path -LiteralPath $Envelope) {
    throw "Refusing to replace existing release envelope: $Envelope"
}
if ($PrivateKeyPath.StartsWith($Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
    $PrivateKeyPath.Equals($Root, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The canonical private key must remain outside the physical candidate directory.'
}

& $Signer sign `
    --manifest $Manifest `
    --private-key $PrivateKeyPath `
    --trust $Trust `
    --key-id $KeyId `
    --out $Envelope
if ($LASTEXITCODE -ne 0) { throw 'Initial release signing failed.' }

$ManifestDocument = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
$ManifestSchema = [string]$ManifestDocument.'$schema'
$SupportedSchemas = @(
    'prototype-ordax.release-manifest/1',
    'prototype-ordax.release-manifest/2',
    'prototype-ordax.release-manifest/3',
    'prototype-ordax.release-manifest/4'
)
if ($ManifestSchema -notin $SupportedSchemas) {
    throw "Signed manifest schema is not recognized by this runbook: $ManifestSchema"
}
$ArtifactNames = @($ManifestDocument.artifacts | ForEach-Object { [string]$_.name })
if ($ArtifactNames.Count -eq 0) {
    throw 'Signed manifest does not bind any artifacts.'
}

$EnvelopeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Envelope).Hash.ToLowerInvariant()
$ManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Manifest).Hash.ToLowerInvariant()
Write-Host ''
Write-Host 'INITIAL_RELEASE_SIGNED=YES'
Write-Host "RELEASE_MANIFEST_SHA256=$ManifestHash"
Write-Host "RELEASE_ENVELOPE_SHA256=$EnvelopeHash"
Write-Host "RELEASE_ENVELOPE_PATH=$Envelope"
Write-Host "RELEASE_MANIFEST_SCHEMA=$ManifestSchema"
Write-Host "RELEASE_BOUND_ARTIFACTS=$($ArtifactNames -join ',')"
Write-Host "PRIVATE_KEY_PATH=$PrivateKeyPath"
Write-Host 'PRIVATE_KEY_COPIED_TO_PACKAGE=NO'
Write-Host 'READY_FOR_RELEASE_PUBLICATION_REVIEW=YES'
Write-Host ''
Write-Host 'release-envelope.json is public material and must travel with the exact artifacts bound by the signed manifest.'
Write-Host 'For release-manifest/4 that means system.erofs, native-surface-runtime.erofs and local-ai-runtime.erofs.'
Write-Host 'Signing alone does not publish, activate, authorize physical media, or select a USB target.'
Write-Host 'Next: run .\\5-Verify-PortableV4-SignedHandoff.ps1 before any publication/materialization review.'
Write-Host 'The private PEM must remain in local private storage and must never be uploaded.'
