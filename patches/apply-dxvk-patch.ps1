param()
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$dxvk = Join-Path $repository 'dxvk'
$patch = Join-Path $PSScriptRoot 'dxvk-portal-startup.patch'
if (-not (Test-Path -LiteralPath (Join-Path $dxvk '.git'))) {
    throw 'DXVK is missing. Run git submodule update --init --recursive first.'
}
# Windows PowerShell 5.1 turns redirected native stderr into a terminating
# error under 'Stop'; these probes are expected to fail on one branch.
$ErrorActionPreference = 'Continue'
& git -C $dxvk apply --ignore-whitespace --reverse --check -- $patch 2>$null
$alreadyApplied = $LASTEXITCODE -eq 0
if (-not $alreadyApplied) { & git -C $dxvk apply --ignore-whitespace --check -- $patch }
$applies = $LASTEXITCODE -eq 0
$ErrorActionPreference = 'Stop'
if ($alreadyApplied) { Write-Host 'DXVK Portal patch is already applied.'; exit 0 }
if (-not $applies) { throw 'DXVK patch does not match this checkout; preserve your changes and check the submodule revision.' }
& git -C $dxvk apply --ignore-whitespace -- $patch
if ($LASTEXITCODE -ne 0) { throw 'Failed to apply the DXVK Portal patch.' }
Write-Host 'Applied the DXVK Portal patch.'
