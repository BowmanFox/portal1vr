param([string]$Configuration = 'Release', [string]$PlatformToolset = 'v143')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'patches\apply-dxvk-patch.ps1')
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Install Visual Studio C++ build tools and a Windows SDK.' }
$msbuild = & $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1
if (-not $msbuild) { throw 'MSBuild was not found.' }
# The pinned project emits one shared PDB.  Serializing MSBuild and CL avoids
# C2471 when newer MSBuild versions pair with the v143 compiler.
& $msbuild (Join-Path $PSScriptRoot 'l4d2vr.sln') /m:1 /p:MultiProcessorCompilation=false "/p:Configuration=$Configuration" /p:Platform=x86 "/p:PlatformToolset=$PlatformToolset" /p:PostBuildEventUseInBuild=false
if ($LASTEXITCODE -ne 0) { throw 'Portal VR build failed.' }
Write-Host 'Built d3d9.dll. Run L4D2VR\copy-to-portal.ps1 to install it after closing Portal.'
