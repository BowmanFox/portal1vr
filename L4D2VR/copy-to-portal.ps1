param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDll,
    [string]$PortalDirectory
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDll)) {
    throw "Build output not found: $SourceDll"
}

function Get-SteamLibraryPaths {
    $roots = @(
        "${env:ProgramFiles(x86)}\\Steam",
        "${env:ProgramFiles}\\Steam",
        "${env:ProgramW6432}\\Steam"
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

    $libraries = New-Object System.Collections.Generic.List[string]

    foreach ($root in $roots) {
        $libraries.Add($root)

        $vdfPath = Join-Path $root "steamapps\\libraryfolders.vdf"
        if (-not (Test-Path -LiteralPath $vdfPath)) {
            continue
        }

        $content = Get-Content -LiteralPath $vdfPath -Raw
        $matches = [regex]::Matches($content, '"path"\s+"([^"]+)"')
        foreach ($match in $matches) {
            $libraryPath = $match.Groups[1].Value -replace "\\\\", "\"
            if ($libraryPath) {
                $libraries.Add($libraryPath)
            }
        }
    }

    foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Select-Object -ExpandProperty Root)) {
        foreach ($suffix in @("", "Steam", "SteamLibrary", "Games\\Steam", "Games\\SteamLibrary")) {
            $candidate = if ($suffix) { Join-Path $drive $suffix } else { $drive }
            if (Test-Path -LiteralPath $candidate) {
                $libraries.Add($candidate)
            }
        }
    }

    return $libraries | Select-Object -Unique
}

$portalDir = $PortalDirectory
foreach ($library in $(if (-not $portalDir) { Get-SteamLibraryPaths })) {
    $candidate = Join-Path $library "steamapps\\common\\Portal"
    if (Test-Path -LiteralPath $candidate) {
        $portalDir = $candidate
        break
    }
}

if (-not $portalDir) {
    Write-Host "Portal install not found. Skipping DLL copy."
    exit 0
}

if (-not (Test-Path -LiteralPath (Join-Path $portalDir "hl2.exe"))) {
    throw "Not a Portal installation: $portalDir"
}

$binDir = Join-Path $portalDir "bin"
if (-not (Test-Path -LiteralPath $binDir)) {
    New-Item -ItemType Directory -Path $binDir | Out-Null
}

$vrDir = Join-Path $binDir "VR"
if (-not (Test-Path -LiteralPath $vrDir)) {
    New-Item -ItemType Directory -Path $vrDir | Out-Null
}

$vrActionDir = Join-Path $vrDir "SteamVRActionManifest"
if (-not (Test-Path -LiteralPath $vrActionDir)) {
    New-Item -ItemType Directory -Path $vrActionDir | Out-Null
}

$openVrSource = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\thirdparty\openvr\bin\win32\openvr_api.dll"))
$manifestSource = Join-Path $PSScriptRoot "manifest.vrmanifest"
$capsuleSource = Join-Path $PSScriptRoot "portal1vr_capsule_main.png"
$portraitSource = Join-Path $PSScriptRoot "portal1vr_portrait_main.png"
$runtimeFiles = @(
    @{
        Source = Join-Path $PSScriptRoot '..\Launch Portal VR.cmd'
        Destination = Join-Path $portalDir 'Launch Portal VR.cmd'
        Label = 'Launch Portal VR.cmd'
    },
    @{
        Source = $SourceDll
        Destination = Join-Path $binDir "d3d9.dll"
        Label = "d3d9.dll"
    },
    @{
        Source = $openVrSource
        Destination = Join-Path $binDir "openvr_api.dll"
        Label = "openvr_api.dll"
    },
    @{
        Source = $manifestSource
        Destination = Join-Path $vrDir "manifest.vrmanifest"
        Label = "manifest.vrmanifest"
    },
    @{
        Source = $capsuleSource
        Destination = Join-Path $vrDir "portal1vr_capsule_main.png"
        Label = "portal1vr_capsule_main.png"
    },
    @{
        Source = $portraitSource
        Destination = Join-Path $vrDir "portal1vr_portrait_main.png"
        Label = "portal1vr_portrait_main.png"
    }
)

foreach ($file in $runtimeFiles) {
    if (-not (Test-Path -LiteralPath $file.Source)) {
        throw "Required runtime file was not found: $($file.Source)"
    }

    try {
        Copy-Item -LiteralPath $file.Source -Destination $file.Destination -Force
        Write-Host "Copied $($file.Label) to $($file.Destination)"
    }
    catch {
        if ($_.Exception.Message -like "*being used by another process*") {
            throw "Close Portal before installing: '$($file.Destination)' is in use."
        }

        throw
    }
}

$actionManifestSourceDir = Join-Path $PSScriptRoot "SteamVRActionManifest"
if (Test-Path -LiteralPath $actionManifestSourceDir) {
    Get-ChildItem -LiteralPath $actionManifestSourceDir -File | Copy-Item -Destination $vrActionDir -Force
    Write-Host "Copied SteamVRActionManifest to $vrActionDir"
}
else {
    throw "SteamVRActionManifest source directory was not found: $actionManifestSourceDir"
}

$configDestination = Join-Path $vrDir "config.txt"
if (-not (Test-Path -LiteralPath $configDestination)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "config.txt") -Destination $configDestination
}
else {
    # Existing installs keep their chosen settings, but older configs do not
    # know about the optional body-render settings. Add only those missing
    # lines so the parser does not show a warning dialog at startup.
    $configText = [System.IO.File]::ReadAllText($configDestination)
    $bodyConfigLines = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot "config.txt") |
        Where-Object { $_ -match '^(FirstPersonBody|FirstPersonBodyHideUpper)=' })
    $missingBodyConfigLines = @($bodyConfigLines | Where-Object {
        $key = ($_ -split '=', 2)[0]
        $configText -notmatch ('(?m)^' + [regex]::Escape($key) + '=')
    })
    if ($missingBodyConfigLines.Count -gt 0) {
        $newline = [Environment]::NewLine
        $prefix = if ($configText.EndsWith("`n") -or $configText.EndsWith("`r")) { '' } else { $newline }
        [System.IO.File]::AppendAllText(
            $configDestination,
            $prefix + ($missingBodyConfigLines -join $newline) + $newline)
        Write-Host "Added missing first-person body settings to $configDestination"
    }
}

$materialSource = Join-Path $PSScriptRoot "materials"
$materialDestination = Join-Path $portalDir "portal\custom\portal1vr\materials"
if (Test-Path -LiteralPath $materialSource) {
    New-Item -ItemType Directory -Force -Path $materialDestination | Out-Null
    Get-ChildItem -LiteralPath $materialSource -Directory | Copy-Item -Destination $materialDestination -Recurse -Force
    Write-Host "Installed corrected arm materials"
}

$customVpkSource = Join-Path $PSScriptRoot "custom\bowman_portal1.vpk"
$customVpkDestination = Join-Path $portalDir "portal\custom\bowman_portal1.vpk"
if (Test-Path -LiteralPath $customVpkSource) {
    New-Item -ItemType Directory -Force -Path (Split-Path $customVpkDestination) | Out-Null
    Copy-Item -LiteralPath $customVpkSource -Destination $customVpkDestination -Force
    Write-Host "Installed custom viewmodel and playermodel VPK"
}
