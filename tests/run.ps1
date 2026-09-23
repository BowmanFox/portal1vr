param([string]$PortalClient = '')
$ErrorActionPreference='Stop'
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'Run this from an x86 Native Tools Command Prompt for Visual Studio.' }
$repository=Split-Path -Parent $PSScriptRoot
$output=Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Force $output | Out-Null
& cl.exe /nologo /std:c++17 /EHsc /RTC1 /Od /DWIN32 /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS "/I$repository\L4D2VR" "/I$repository\L4D2VR\sdk" (Join-Path $PSScriptRoot 'abi.cpp') "/Fe$output\abi.exe" "/Fo$output\abi.obj"
if ($LASTEXITCODE -ne 0) { throw 'ABI test build failed.' }
& (Join-Path $output 'abi.exe')
if ($LASTEXITCODE -ne 0) { throw 'ABI tests failed.' }
if ($PortalClient) {
    & cl.exe /nologo /std:c++17 /EHsc /RTC1 /Od /DWIN32 /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS "/I$repository\L4D2VR" "/I$repository\L4D2VR\sdk" (Join-Path $PSScriptRoot 'portal-client-layout.cpp') "/Fe$output\portal-client-layout.exe" "/Fo$output\portal-client-layout.obj"
    if ($LASTEXITCODE -ne 0) { throw 'Portal client layout test build failed.' }
    & (Join-Path $output 'portal-client-layout.exe') $PortalClient
    if ($LASTEXITCODE -ne 0) { throw 'Installed Portal client layout is not supported by the portal-aware trace.' }
}
