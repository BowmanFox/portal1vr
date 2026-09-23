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
    # Preserve chosen settings and append every missing shipped default. A
    # hand-maintained list missed the grip and body-offset settings, causing
    # one blocking startup dialog for each absent entry.
    $configText = [System.IO.File]::ReadAllText($configDestination)
    $defaultConfigLines = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot "config.txt") |
        Where-Object { $_ -match '^[A-Za-z0-9_]+=' })
    $missingConfigLines = @($defaultConfigLines | Where-Object {
        $key = ($_ -split '=', 2)[0]
        # Runtime keys are case-sensitive, including when checking presence.
        $configText -cnotmatch ('(?m)^' + [regex]::Escape($key) + '=')
    })
    if ($missingConfigLines.Count -gt 0) {
        $newline = [Environment]::NewLine
        $prefix = if ($configText.EndsWith("`n") -or $configText.EndsWith("`r")) { '' } else { $newline }
        [System.IO.File]::AppendAllText(
            $configDestination,
            $prefix + ($missingConfigLines -join $newline) + $newline)
        Write-Host "Added $($missingConfigLines.Count) missing default settings to $configDestination"
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
$customVpkArchive = Join-Path $PSScriptRoot "custom\bowman_portal1.zip"
$customVpkDestination = Join-Path $portalDir "portal\custom\bowman_portal1.vpk"
$customVpkInstalled = $false
if (Test-Path -LiteralPath $customVpkArchive) {
    # Store the losslessly compressed model in Git; Source still loads a VPK.
    # Extract only the expected file so archive paths cannot escape custom/.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $modelArchive = [IO.Compression.ZipFile]::OpenRead($customVpkArchive)
    try {
        if ($modelArchive.Entries.Count -ne 1 -or $modelArchive.Entries[0].FullName -ne 'bowman_portal1.vpk') {
            throw 'The Bowman model archive must contain only bowman_portal1.vpk.'
        }
        New-Item -ItemType Directory -Force -Path (Split-Path $customVpkDestination) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($modelArchive.Entries[0], $customVpkDestination, $true)
    } finally {
        $modelArchive.Dispose()
    }
    $customVpkInstalled = $true
    Write-Host "Installed custom viewmodel and playermodel VPK"
} elseif (Test-Path -LiteralPath $customVpkSource) {
    New-Item -ItemType Directory -Force -Path (Split-Path $customVpkDestination) | Out-Null
    Copy-Item -LiteralPath $customVpkSource -Destination $customVpkDestination -Force
    $customVpkInstalled = $true
    Write-Host "Installed custom viewmodel and playermodel VPK"
}

if ($customVpkInstalled) {
    # Older radio installers left a loose WAV that can mask the bundled song.
    # Keep those files outside custom/ so Source loads only the new VPK copy.
    $customRoot = [IO.Path]::GetFullPath((Join-Path $portalDir 'portal\custom'))
    $retiredRadioFiles = @(
        'portal1vr\sound\ambient\music\looping_radio_mix.wav',
        'portal1vr\portal1vr_streamer_warning.txt',
        'portal1vr\sound\sound.cache',
        'bowman_portal1.vpk.sound.cache'
    )
    $radioBackupRoot = Join-Path $portalDir ('bin\VR\InstallBackups\radio-' +
        [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff'))
    foreach ($relativePath in $retiredRadioFiles) {
        $oldFile = [IO.Path]::GetFullPath((Join-Path $customRoot $relativePath))
        if (-not $oldFile.StartsWith($customRoot + [IO.Path]::DirectorySeparatorChar,
                [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Radio migration path escaped the custom directory.'
        }
        if (Test-Path -LiteralPath $oldFile -PathType Leaf) {
            $backupFile = Join-Path $radioBackupRoot $relativePath
            New-Item -ItemType Directory -Force -Path (Split-Path $backupFile) | Out-Null
            Move-Item -LiteralPath $oldFile -Destination $backupFile
            Write-Host "Backed up obsolete radio override/cache: $backupFile"
        }
    }
}
