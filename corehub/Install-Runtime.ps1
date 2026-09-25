param(
 [Parameter(Mandatory=$true)][string]$GameRoot,
 [string]$SourceDll=(Join-Path $PSScriptRoot '..\Release\d3d9.dll')
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $GameRoot).Path
$repo=Split-Path -Parent $PSScriptRoot
if (!(Test-Path -LiteralPath (Join-Path $root 'hl2.wrap.exe'))) {throw 'Select the native 2009 Corehub installation.'}
$expected=@{
 'portal2\bin\Client.dll'='329b788ff0c5e744403086eea7e455c2c113344371f072a0829dbd4f731a3d4b'
 'portal2\bin\Server.dll'='1dc9c9ac0e12511b21beac4c183462df53b504920421e52e66e96e926659c948'
 'bin\engine.dll'='f2b2b02abdf9504ec77708e0205a02f33e7ef8e3e6fd2e81423adfa4533ad228'
 'bin\MaterialSystem.dll'='a7d83e3549a93f8918b4a92d41dc6124f018b2785a8a70f9c2ed12fcd66ae276'
 'bin\shaderapidx9.dll'='7b86f32602fe813b0ee03debbc45c4b184ed01c92f2e2b5667f4ca9d76f67ffc'
}
foreach($item in $expected.GetEnumerator()) {
 if((Get-FileHash -LiteralPath (Join-Path $root $item.Key) -Algorithm SHA256).Hash -ne $item.Value) {throw "Unsupported Corehub binary: $($item.Key)"}
}
$running=Get-CimInstance Win32_Process -Filter "Name='hl2.exe' OR Name='hl2.wrap.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)}
if($running){throw 'Close this Corehub game before installing the runtime.'}
$files=@{'bin\d3d9.dll'=(Resolve-Path -LiteralPath $SourceDll).Path;'bin\openvr_api.dll'=(Join-Path $repo 'thirdparty\openvr\bin\win32\openvr_api.dll')}
foreach($file in Get-ChildItem -LiteralPath (Join-Path $repo 'L4D2VR\SteamVRActionManifest') -File -Filter '*.json') {
 $files['bin\VR\SteamVRActionManifest\'+$file.Name]=$file.FullName
}
foreach($profile in @('bowman_singleplayer','bowman_coop')) {
 if(Test-Path -LiteralPath (Join-Path $root "$profile\gameinfo.txt")) {
  $launcher=if($profile -eq 'bowman_singleplayer'){'Launch Bowman Single-player.cmd'}else{'Launch Bowman Co-op.cmd'}
  $files[$launcher]=Join-Path $PSScriptRoot ('launchers\'+$launcher)
  foreach($file in Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'runtime-assets\models\weapons') -File) {
   $files["$profile\models\weapons\"+$file.Name]=$file.FullName
  }
 }
}
foreach($source in $files.Values){if(!(Test-Path -LiteralPath $source)){throw "Missing runtime file: $source"}}
$backup=Join-Path $root ('corehub_vr_backups\'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
$audit=@()
foreach($item in $files.GetEnumerator()) {
 $target=Join-Path $root $item.Key
 if(Test-Path -LiteralPath $target){$copy=Join-Path $backup $item.Key;New-Item -ItemType Directory -Force -Path (Split-Path $copy) | Out-Null;Copy-Item -LiteralPath $target -Destination $copy}
 New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
 Copy-Item -LiteralPath $item.Value -Destination $target
 $hash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
 if($hash -ne (Get-FileHash -LiteralPath $item.Value -Algorithm SHA256).Hash){throw "Installed hash mismatch: $target"}
 $audit+=@{path=$item.Key;sha256=$hash}
}
New-Item -ItemType Directory -Force -Path $backup | Out-Null
@{installed=$audit;backup=$backup;game=$root;build='Corehub 3916'} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'installation.json')
Write-Output "Installed and verified $($files.Count) Corehub runtime files. Backup: $backup"
