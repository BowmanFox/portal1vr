param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDll
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

$portalDir = $null
foreach ($library in Get-SteamLibraryPaths) {
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
        Write-Warning "Skipped $($file.Label) copy because the source file was not found: $($file.Source)"
        continue
    }

    try {
        Copy-Item -LiteralPath $file.Source -Destination $file.Destination -Force
        Write-Host "Copied $($file.Label) to $($file.Destination)"
    }
    catch {
        if ($_.Exception.Message -like "*being used by another process*") {
            Write-Warning "Skipped $($file.Label) copy because '$($file.Destination)' is in use. Close Portal to deploy the new build."
            continue
        }

        throw
    }
}

$actionManifestSourceDir = Join-Path $PSScriptRoot "SteamVRActionManifest"
if (Test-Path -LiteralPath $actionManifestSourceDir) {
    Copy-Item -LiteralPath (Join-Path $actionManifestSourceDir "*") -Destination $vrActionDir -Recurse -Force
    Write-Host "Copied SteamVRActionManifest to $vrActionDir"
}
else {
    Write-Warning "Skipped SteamVRActionManifest copy because the source directory was not found: $actionManifestSourceDir"
}
