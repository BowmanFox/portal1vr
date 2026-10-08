# Pushes the current r10 work (push_github.ps1) to GitHub every $Minutes minutes until the PC shuts down,
# or until r10\FINALIZED exists (then it makes one last push and stops). Runs hidden; every attempt is
# appended to r10\push_loop.log. Started by autostart.ps1 at logon; only one copy runs at a time.
param([int]$Minutes = 30, [int]$FirstDelayMinutes = 30)
$r10 = $PSScriptRoot
$logFile = Join-Path $r10 'push_loop.log'
$single = New-Object System.Threading.Mutex($false, 'CorehubR10PushLoop')
if (-not $single.WaitOne(0)) { exit 0 }
Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] loop started (pid $PID, every $Minutes min)" -Encoding Ascii
Start-Sleep -Seconds ($FirstDelayMinutes * 60)
while ($true) {
    $stamp = Get-Date -Format o
    $final = Test-Path (Join-Path $r10 'FINALIZED')
    try {
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $r10 'push_github.ps1') 2>&1 | Out-String
        $lines = ($out -split "`r?`n") | Where-Object { $_ -and $_ -notmatch 'CRLF' }
        Add-Content -LiteralPath $logFile -Value "[$stamp] exit $LASTEXITCODE`r`n$(($lines | Select-Object -Last 12) -join "`r`n")" -Encoding Ascii
    } catch {
        Add-Content -LiteralPath $logFile -Value "[$stamp] FAILED $($_.Exception.Message)" -Encoding Ascii
    }
    if ($final) { Add-Content -LiteralPath $logFile -Value "[$(Get-Date -Format o)] FINALIZED - loop stopped" -Encoding Ascii; break }
    Start-Sleep -Seconds ($Minutes * 60)
}
