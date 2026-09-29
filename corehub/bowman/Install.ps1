param([Parameter(Mandatory=$true)][string]$GameRoot)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $GameRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $root 'hl2.wrap.exe'))) { throw 'Select the 2009 Corehub installation root.' }
$package=Join-Path $PSScriptRoot 'Bowman_Corehub_Models.zip'
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package-manifest.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $manifest.package_sha256) {throw 'Package checksum mismatch.'}
function Get-SafePackagePath([string]$Path) {
 if ([string]::IsNullOrWhiteSpace($Path) -or [IO.Path]::IsPathRooted($Path) -or $Path.Contains(':')) {throw "Unsafe package path: $Path"}
 $relative=$Path.Replace('/','\')
 if (($relative.Split('\') | Where-Object {$_ -eq '..' -or $_ -eq '.' -or $_ -eq '' -or $_.TrimEnd(' ','.') -ne $_}).Count) {throw "Unsafe package path: $Path"}
 if ($relative -notin @('Launch Bowman Co-op.cmd','Launch Bowman Single-player.cmd') -and -not $relative.StartsWith('bowman_coop\',[StringComparison]::OrdinalIgnoreCase) -and -not $relative.StartsWith('bowman_singleplayer\',[StringComparison]::OrdinalIgnoreCase)) {throw "Unexpected package path: $Path"}
 return $relative
}
$expected=@{}
foreach($file in $manifest.files) {
 $relative=Get-SafePackagePath $file.path
 if ($expected.ContainsKey($relative)) {throw "Duplicate manifest path: $relative"}
 if ($file.sha256 -notmatch '^[0-9a-fA-F]{64}$') {throw "Invalid file checksum: $relative"}
 $expected[$relative]=$file
}
if ($expected.Count -eq 0) {throw 'Empty package manifest.'}
$staging=Join-Path ([IO.Path]::GetTempPath()) ('bowman-corehub-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $staging | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead($package)
try {
 $seen=@{}
 foreach($entry in $zip.Entries) {
  $relative=Get-SafePackagePath $entry.FullName
  if ($seen.ContainsKey($relative) -or -not $expected.ContainsKey($relative)) {throw "Unexpected or duplicate ZIP entry: $relative"}
  $seen[$relative]=$true
  $target=[IO.Path]::GetFullPath((Join-Path $staging $relative))
  if (-not $target.StartsWith($staging+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe package path.'}
 }
 if ($seen.Count -ne $expected.Count) {throw 'ZIP and manifest file lists differ.'}
} finally {$zip.Dispose()}
Expand-Archive -LiteralPath $package -DestinationPath $staging
$backup=Join-Path $root ('bowman_coop_backups\'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
$installed=0
foreach($file in $manifest.files) {
 $relative=$file.path.Replace('/','\')
 $source=Join-Path $staging $relative
 if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $file.sha256) {throw "File checksum mismatch: $relative"}
}
foreach($file in $manifest.files) {
 $relative=$file.path.Replace('/','\');$source=Join-Path $staging $relative;$target=[IO.Path]::GetFullPath((Join-Path $root $relative))
 if (-not $target.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe install destination.'}
 if (Test-Path -LiteralPath $target) {
  $copy=Join-Path $backup $relative;New-Item -ItemType Directory -Force -Path (Split-Path $copy) | Out-Null;Copy-Item -LiteralPath $target -Destination $copy
 }
 New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
 Copy-Item -LiteralPath $source -Destination $target
 if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $file.sha256) {throw "Installed hash mismatch: $relative"}
 $installed++
}
Write-Output "Installed and verified $installed files. Use Launch Bowman Co-op.cmd or Launch Bowman Single-player.cmd."
Write-Output "Existing files, if any, were backed up under $backup"
