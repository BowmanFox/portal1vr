param()
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$dxvk = Join-Path $repository 'dxvk'
$patch = Join-Path $PSScriptRoot 'dxvk-portal-startup.patch'
if (-not (Test-Path -LiteralPath (Join-Path $dxvk '.git'))) {
    throw 'DXVK is missing. Run git submodule update --init --recursive first.'
}
& git -C $dxvk apply --reverse --check -- $patch 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host 'DXVK Portal patch is already applied.'; exit 0 }
& git -C $dxvk apply --check -- $patch
if ($LASTEXITCODE -ne 0) { throw 'DXVK patch does not match this checkout; preserve your changes and check the submodule revision.' }
& git -C $dxvk apply -- $patch
if ($LASTEXITCODE -ne 0) { throw 'Failed to apply the DXVK Portal patch.' }
Write-Host 'Applied the DXVK Portal patch.'
