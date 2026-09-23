$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$fixtureSource = Join-Path $repository 'L4D2VR'
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('portal1vr-config-test-' + [Guid]::NewGuid().ToString('N'))
$vrDir = Join-Path $fixture 'VR'
New-Item -ItemType Directory -Force -Path $vrDir | Out-Null
$path = Join-Path $vrDir 'config.txt'
$script = [IO.File]::ReadAllText((Join-Path $fixtureSource 'copy-to-portal.ps1'))
$start = $script.IndexOf('$configDestination =')
$end = $script.IndexOf('$materialSource =', $start)
if ($start -lt 0 -or $end -le $start) { throw 'Missing config install block' }
$block = [scriptblock]::Create($script.Substring($start, $end - $start).Replace('$PSScriptRoot', '$fixtureSource'))
$defaults = [IO.File]::ReadAllText((Join-Path $fixtureSource 'config.txt'))
$runtime = [IO.File]::ReadAllText((Join-Path $fixtureSource 'vr.cpp'))
$runtime = [regex]::Replace($runtime, '(?s)/\*.*?\*/', '')
$required = @([regex]::Matches($runtime, 'parseOrDefault\("([^"]+)"') | ForEach-Object { $_.Groups[1].Value })
foreach ($match in [regex]::Matches($runtime, 'parseXYZOrDefaultZero\("([^"]+)"')) {
    foreach ($axis in 'X', 'Y', 'Z') { $required += $match.Groups[1].Value + $axis }
}
function Get-MissingRuntimeKeys([string]$text) {
    # Match the runtime's exact, case-sensitive keys before '='.
    @($required | Where-Object { $text -cnotmatch ('(?m)^' + [regex]::Escape($_) + '=') })
}
if (@(Get-MissingRuntimeKeys $defaults).Count) { throw 'Shipped defaults omit a runtime key' }
& $block
if ([IO.File]::ReadAllText($path) -cne $defaults) { throw 'Fresh install differs from shipped defaults' }

$old = ($defaults -split '\r?\n' | Where-Object {
    $_ -notmatch '^(LeftHandGunGrip|LeftHandGunGripRadius|FirstPersonBodyBackOffset)='
}) -join "`r`n"
$old = $old.TrimEnd("`r", "`n") + "`r`nCustomUserSetting=keep-me" # No final newline.
if (@(Get-MissingRuntimeKeys $old).Count -ne 3) { throw 'Fixture does not reproduce the three startup warnings' }
[IO.File]::WriteAllText($path, $old)
& $block
$updated = [IO.File]::ReadAllText($path)
if (-not $updated.StartsWith($old, [StringComparison]::Ordinal)) { throw 'Existing config text changed' }
if (@(Get-MissingRuntimeKeys $updated).Count) { throw 'Runtime would still show a missing-key warning' }
foreach ($setting in 'LeftHandGunGrip=true', 'LeftHandGunGripRadius=6', 'FirstPersonBodyBackOffset=8') {
    if ($updated -cnotmatch ('(?m)^' + [regex]::Escape($setting) + '(?:\s|$)')) { throw "Wrong default: $setting" }
}
& $block
if ([IO.File]::ReadAllText($path) -cne $updated) { throw 'Repeated installation changed config' }

$custom = $updated.Replace('LeftHandGunGrip=true', 'LeftHandGunGrip=false').Replace('LeftHandGunGripRadius=6', 'LeftHandGunGripRadius=9').Replace('FirstPersonBodyBackOffset=8', 'FirstPersonBodyBackOffset=12')
[IO.File]::WriteAllText($path, $custom)
& $block
if ([IO.File]::ReadAllText($path) -cne $custom) { throw 'Custom grip/body values were overwritten' }

# A differently capitalized key does not satisfy the C++ parser.
[IO.File]::WriteAllText($path, $custom.Replace('LeftHandGunGrip=false', 'lefthandgungrip=false'))
& $block
if (@(Get-MissingRuntimeKeys ([IO.File]::ReadAllText($path))).Count) { throw 'Case mismatch still leaves a runtime key missing' }
Write-Output "PASS: all $($required.Count) runtime keys covered, three reported warnings reproduced and repaired, fresh installs, custom values, comments, missing final newline, case-sensitive keys, and repeated installation."
