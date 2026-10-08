# Corehub build/capture watcher. Start it once with start-watcher.cmd and leave
# the window open. Claude drops request files into .\requests and this runs
# them, so no clicks (and no repeated app-access prompts) are needed:
#   requests\build-*.req    -> runs build_intro.py (VMF, director, timeline)
#   requests\movie-*.req    -> runs r10\record_movie.ps1 <args> (continuous 60 fps test video)
#   requests\capture-*.req  -> runs iterate.ps1 -SkipBuild <file contents>,
#                              e.g. "-Prefix r9p -Range 0:32:0.5", and brings the
#                              game window to the front so its audio plays.
# Compile and pack are done by Claude through hammer-mcp between the two.
# Progress for each request goes to requests\<name>.log, ending in a DONE line.
$ErrorActionPreference = 'Continue'
$work = $PSScriptRoot
$task = (Resolve-Path (Join-Path $work '..\..')).Path
$python = Join-Path $work '.re-venv\Scripts\python.exe'
$req = Join-Path $work 'requests'
New-Item -ItemType Directory -Force $req | Out-Null
$host.UI.RawUI.WindowTitle = 'Corehub watcher - leave open'

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class CorehubFocus {
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] static extern void keybd_event(byte k, byte s, uint f, UIntPtr e);
    public static bool Bring(IntPtr h) {
        // A tap of Alt lets a background process hand focus to another window.
        keybd_event(0x12, 0, 0, UIntPtr.Zero);
        keybd_event(0x12, 0, 2, UIntPtr.Zero);
        ShowWindow(h, 9);
        return SetForegroundWindow(h);
    }
}
"@

function Write-Log([string]$log, [string]$text) {
    Add-Content -LiteralPath $log -Value $text -Encoding Ascii
}

Write-Host "Watching $req (Ctrl+C or close this window to stop)"
while ($true) {
    $pending = Get-ChildItem -LiteralPath $req -Filter '*.req' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime
    foreach ($item in $pending) {
        $name = $item.BaseName
        $reqArgs = (Get-Content -LiteralPath $item.FullName -Raw)
        if ($null -eq $reqArgs) { $reqArgs = '' }
        $reqArgs = $reqArgs.Trim()
        Remove-Item -LiteralPath $item.FullName -ErrorAction SilentlyContinue
        $log = Join-Path $req "$name.log"
        Set-Content -LiteralPath $log -Value "START $(Get-Date -Format o) $reqArgs" -Encoding Ascii
        Write-Host "$(Get-Date -Format T) $name $reqArgs"
        try {
            if ($name -like 'build*') {
                Push-Location -LiteralPath $task
                try {
                    & $python (Join-Path $work 'build_intro.py') 2>&1 | ForEach-Object { "$_" } |
                        Out-File -LiteralPath $log -Append -Encoding ascii
                    Write-Log $log "EXIT $LASTEXITCODE"
                } finally { Pop-Location }
            } elseif ($name -like 'capture*' -or $name -like 'movie*') {
                $out = Join-Path $req "$name.out.txt"
                $errOut = Join-Path $req "$name.err.txt"
                if ($name -like 'movie*') {
                    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $work 'r10\record_movie.ps1')`" $reqArgs"
                } else {
                    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $work 'iterate.ps1')`" -SkipBuild $reqArgs"
                }
                $p = Start-Process powershell.exe -ArgumentList $argList -PassThru -NoNewWindow `
                    -RedirectStandardOutput $out -RedirectStandardError $errOut
                $focused = $false
                while (-not $p.HasExited) {
                    if (-not $focused) {
                        $game = Get-Process -Name hl2 -ErrorAction SilentlyContinue |
                            Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
                        if ($game) {
                            Start-Sleep -Seconds 2
                            $ok = [CorehubFocus]::Bring($game.MainWindowHandle)
                            Write-Log $log "FOCUS game window: $ok"
                            $focused = $true
                        }
                    }
                    Start-Sleep -Milliseconds 500
                }
                $p.WaitForExit()
                if (Test-Path $out) { Get-Content -LiteralPath $out | ForEach-Object { Write-Log $log $_ } }
                if (Test-Path $errOut) { Get-Content -LiteralPath $errOut | ForEach-Object { Write-Log $log "ERR $_" } }
                Write-Log $log "EXIT $($p.ExitCode)"
                # Captures overwrite mapspawn/autoexec; put the normal player setup back.
                $normal = Join-Path $work 'r10\normal-runtime'
                $modDir = Join-Path $work 'runtime\game\corehub_intro'
                if (Test-Path (Join-Path $normal 'mapspawn.nut')) {
                    Copy-Item -LiteralPath (Join-Path $normal 'mapspawn.nut') -Destination (Join-Path $modDir 'scripts\vscripts\mapspawn.nut') -Force
                    Copy-Item -LiteralPath (Join-Path $normal 'autoexec.cfg') -Destination (Join-Path $modDir 'cfg\autoexec.cfg') -Force
                    Write-Log $log "normal runtime restored"
                }
            } else {
                Write-Log $log "UNKNOWN request type"
            }
        } catch {
            Write-Log $log "FAILED $($_.Exception.Message)"
        }
        Write-Log $log "DONE $(Get-Date -Format o)"
        Write-Host "$(Get-Date -Format T) $name done"
    }
    Start-Sleep -Seconds 2
}
