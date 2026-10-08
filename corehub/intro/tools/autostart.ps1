# Run at Windows logon by "Corehub intro autostart.cmd" in the Startup folder. Until r10\FINALIZED exists it
# keeps the Corehub r10 pipeline going while the PC is on: the request watcher (builds/test recordings that
# Claude queues) and the 30-minute GitHub push loop. Remove the Startup entry to stop it for good.
$r10 = $PSScriptRoot
$work = Split-Path -Parent $r10
if (Test-Path (Join-Path $r10 'FINALIZED')) { exit 0 }
$others = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.ProcessId -ne $PID })
if (-not ($others | Where-Object { $_.CommandLine -like '*-File*watcher.ps1*' })) {
    Start-Process powershell.exe -WindowStyle Minimized -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $work 'watcher.ps1')`""
    'watcher started'
}
if (-not ($others | Where-Object { $_.CommandLine -like '*-File*push_loop.ps1*' })) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $r10 'push_loop.ps1')`" -Minutes 30 -FirstDelayMinutes 10"
    'push loop started'
}
