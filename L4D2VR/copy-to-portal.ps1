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

$destination = Join-Path $binDir "d3d9.dll"
try {
    Copy-Item -LiteralPath $SourceDll -Destination $destination -Force
    Write-Host "Copied d3d9.dll to $destination"
}
catch {
    if ($_.Exception.Message -like "*being used by another process*") {
        Write-Warning "Skipped DLL copy because '$destination' is in use. Close Portal to deploy the new build."
        exit 0
    }

    throw
}
