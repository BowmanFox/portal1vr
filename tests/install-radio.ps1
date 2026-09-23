$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('portal1vr-radio-test-' + [Guid]::NewGuid().ToString('N'))
$fixtureSource = Join-Path $fixture 'source'
$portalDir = Join-Path $fixture 'Portal'
New-Item -ItemType Directory -Force -Path (Join-Path $fixtureSource 'custom') | Out-Null
$installer = [IO.File]::ReadAllText((Join-Path $PSScriptRoot '..\L4D2VR\copy-to-portal.ps1'))
$start = $installer.IndexOf('$customVpkSource =')
if ($start -lt 0) { throw 'Missing model install block' }
$block = [scriptblock]::Create($installer.Substring($start).Replace('$PSScriptRoot', '$fixtureSource'))
$archivePath = Join-Path $fixtureSource 'custom\bowman_portal1.zip'
$sourceVpk = Join-Path $fixtureSource 'custom\bowman_portal1.vpk'
[IO.File]::WriteAllText($sourceVpk, 'new-model-and-instrumental-radio')
$archive = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Create)
try {
    [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $sourceVpk, 'bowman_portal1.vpk') | Out-Null
} finally { $archive.Dispose() }
$retired = @('portal1vr\sound\ambient\music\looping_radio_mix.wav',
    'portal1vr\portal1vr_streamer_warning.txt', 'portal1vr\sound\sound.cache',
    'bowman_portal1.vpk.sound.cache')
foreach ($relative in $retired) {
    $path = Join-Path $portalDir ('portal\custom\' + $relative)
    New-Item -ItemType Directory -Force -Path (Split-Path $path) | Out-Null
    [IO.File]::WriteAllText($path, 'previous:' + $relative)
}
$unrelated = Join-Path $portalDir 'portal\custom\portal1vr\sound\unrelated.wav'
[IO.File]::WriteAllText($unrelated, 'keep-this')
& $block
$installed = Join-Path $portalDir 'portal\custom\bowman_portal1.vpk'
if ((Get-FileHash $installed).Hash -ne (Get-FileHash $sourceVpk).Hash) { throw 'Model bytes changed' }
$backup = @(Get-ChildItem (Join-Path $portalDir 'bin\VR\InstallBackups') -Directory)
if ($backup.Count -ne 1) { throw 'Expected one backup folder' }
foreach ($relative in $retired) {
    if (Test-Path -LiteralPath (Join-Path $portalDir ('portal\custom\' + $relative))) { throw 'Old radio still active' }
    if ([IO.File]::ReadAllText((Join-Path $backup[0].FullName $relative)) -ne ('previous:' + $relative)) { throw 'Backup changed' }
}
if ([IO.File]::ReadAllText($unrelated) -ne 'keep-this') { throw 'Unrelated sound changed' }
& $block
if (@(Get-ChildItem (Join-Path $portalDir 'bin\VR\InstallBackups') -Directory).Count -ne 1) { throw 'Redundant backup created' }
# A malformed archive must fail before touching installed content or old audio.
$archive = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Update)
try { $archive.CreateEntry('../unexpected.vpk') | Out-Null } finally { $archive.Dispose() }
$oldRadio = Join-Path $portalDir ('portal\custom\' + $retired[0])
[IO.File]::WriteAllText($oldRadio, 'preserve-on-failure')
$rejected = $false
try { & $block } catch { $rejected = $_.Exception.Message -like '*must contain only*' }
if (-not $rejected -or [IO.File]::ReadAllText($oldRadio) -ne 'preserve-on-failure') { throw 'Unsafe failed installation' }
if ((Get-FileHash $installed).Hash -ne (Get-FileHash $sourceVpk).Hash) { throw 'Failed install replaced model' }
Write-Output "PASS: exact extraction, reversible radio/cache migration, unrelated files, repeated installation, and malformed archive. Fixture: $fixture"
