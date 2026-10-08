# Records a continuous test run of the published map with the automatic
# reference camera (no player input needed) using Source's startmovie at a
# fixed frame rate, plus the in-game soundtrack (.wav). Normal mapspawn and
# autoexec are restored afterwards so Play.cmd keeps working.
param(
    [Parameter(Mandatory = $true)][string]$Prefix,
    [int]$Fps = 60,
    [int]$Width = 1280,
    [int]$Height = 800,
    [double]$End = 134.4,
    [int]$Quality = 88,
    [string]$Bsp = '',
    [string]$Director = ''
)
$ErrorActionPreference = 'Stop'
# The 2009 engine stops advancing while its window is in the background, so the run keeps the game in
# front -- but only while nobody is using the PC (no input for 30 s), so it never fights the user for focus.
if (-not ('MovieFocus' -as [type])) {
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class MovieFocus {
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] static extern void keybd_event(byte k, byte s, uint f, UIntPtr e);
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LASTINPUTINFO l);
    struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    public static uint IdleMs() { LASTINPUTINFO l = new LASTINPUTINFO(); l.cbSize = 8; GetLastInputInfo(ref l); return unchecked((uint)Environment.TickCount - l.dwTime); }
    public static bool IsFront(IntPtr h) { return GetForegroundWindow() == h; }
    public static bool Bring(IntPtr h) { keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero); ShowWindow(h, 9); return SetForegroundWindow(h); }
}
"@
}
$r10 = $PSScriptRoot
$work = Split-Path -Parent $r10
$task = (Resolve-Path (Join-Path $work '..\..')).Path
$runtime = Join-Path $work 'runtime\game'
$mod = Join-Path $runtime 'corehub_intro'
$exe = Join-Path $runtime 'hl2.exe'
if (-not $Bsp) { $Bsp = Join-Path $task 'outputs\Corehub-Intro\corehub_intro.bsp' }
$normal = Join-Path $r10 'normal-runtime'
$log = Join-Path $mod 'console.log'
$movieDir = Join-Path $mod "movies\$Prefix"

Get-Process -Name hl2 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe } | Stop-Process
Start-Sleep -Seconds 1
Copy-Item -LiteralPath $Bsp -Destination (Join-Path $mod 'maps\corehub_intro.bsp') -Force
# The engine loads the loose director from the mod folder ahead of the copy packed in the BSP,
# so a test run has to put its own director there (the published one is restored afterwards).
$looseDirector = Join-Path $mod 'scripts\vscripts\p9_walkable_v47c\director.nut'
$directorBackup = Join-Path $r10 'normal-runtime\director.loose.nut'
if (-not (Test-Path $directorBackup) -and (Test-Path $looseDirector)) { Copy-Item -LiteralPath $looseDirector -Destination $directorBackup }
if ($Director) { Copy-Item -LiteralPath $Director -Destination $looseDirector -Force; "director $Director" }
if (Test-Path $movieDir) { Remove-Item -LiteralPath $movieDir -Recurse -Force }
New-Item -ItemType Directory -Force $movieDir | Out-Null

$nut = @"
// Movie test run: automatic reference camera, fixed-step recording. Private workspace only.
movD<-null;movStarted<-false;movPrefix<-"$Prefix";
EntFire("intro_director","RunScriptCode","qaReferenceOpening=true;qaMouseLock=true",0.2);
function MovieTick(){
 if(movD==null){local d=Entities.FindByName(null,"intro_director");if(d!=null){d.ValidateScriptScope();movD=d.GetScriptScope();movD.qaReferenceOpening=true;movD.qaMouseLock=true;}}
 if(movD==null||!movD.started){EntFire("worldspawn","RunScriptCode","MovieTick()",0.01);return;}
 local p=movD.player;
 if(!movStarted){
  movStarted=true;
  EntFire("intro_client","Command","cl_mouseenable 0;cl_drawhud 0;r_drawviewmodel 0;con_notifytime 0;developer 0;hud_saytext_time 0;startmovie movies/$Prefix/f jpg wav jpeg_quality $Quality $Quality $Quality $Quality",0,p);
  printl("MOVIE_BEGIN "+movPrefix+" world="+Time()+" start="+movD.startTime);
 }
 local t=Time()-movD.startTime;
 if(t>=$End){
  printl("MOVIE_COMPLETE "+movPrefix+" t="+t);
  EntFire("intro_client","Command","endmovie",0,p);
  EntFire("intro_client","Command","quit",2.0,p);
  return;
 }
 EntFire("worldspawn","RunScriptCode","MovieTick()",0.05);
}
EntFire("worldspawn","RunScriptCode","MovieTick()",0.3);
"@
try {
    Set-Content -LiteralPath (Join-Path $mod 'scripts\vscripts\mapspawn.nut') -Value $nut -Encoding Ascii
    Set-Content -LiteralPath (Join-Path $mod 'cfg\autoexec.cfg') -Encoding Ascii -Value "con_enable 1`ncl_forcepreload 1`nmat_queue_mode 0`ncl_mouseenable 0`nsv_cheats 1`nhost_framerate $Fps`njpeg_quality $Quality`nsnd_mute_losefocus 0`nmat_motion_blur_enabled 0`n"
    $idleWait = (Get-Date).AddMinutes(10)
    while ([MovieFocus]::IdleMs() -lt 60000 -and (Get-Date) -lt $idleWait) { Start-Sleep -Seconds 5 }
    "launch (pc idle $([int]([MovieFocus]::IdleMs() / 1000)) s)"
    $env:SteamAppId = '380'; $env:SteamGameId = '380'
    Start-Process -FilePath (Join-Path $runtime 'hl2.wrap.exe') -WorkingDirectory $runtime -ArgumentList "-game corehub_intro -insecure -windowed -noborder -w $Width -h $Height -novid -condebug -conclearlog -ip 127.0.0.1 -port 27029 +mat_queue_mode 0 +maxplayers 1 +host_framerate $Fps +map corehub_intro"
    $deadline = (Get-Date).AddHours(4)
    $seen = $false; $lastCount = -1; $stall = 0
    do {
        Start-Sleep -Seconds 5
        $done = (Test-Path $log) -and (Select-String -Path $log -Pattern "MOVIE_COMPLETE $Prefix" -Quiet)
        $failed = (Test-Path $log) -and (Select-String -Path $log -Pattern 'FAILED to compile and execute script' -Quiet)
        $alive = Get-Process -Name hl2 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe }
        if ($alive) { $seen = $true }
        $idle = [MovieFocus]::IdleMs()
        $game = $alive | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
        if ($game -and $idle -gt 30000 -and -not [MovieFocus]::IsFront($game.MainWindowHandle)) {
            $ok = [MovieFocus]::Bring($game.MainWindowHandle); "refocus after $([int]($idle / 1000)) s idle: $ok"
        }
        $count = [System.IO.Directory]::GetFiles($movieDir, '*.jpg').Length
        if ($count -ne $lastCount -or $idle -lt 30000) { $lastCount = $count; $stall = 0 } else { $stall += 5 }
    } until ($done -or $failed -or (Get-Date) -gt $deadline -or ($seen -and -not $alive) -or $stall -gt 900)
    Start-Sleep -Seconds 6
    $frames = (Get-ChildItem -LiteralPath $movieDir -Filter '*.jpg' -ErrorAction SilentlyContinue).Count
    "frames $frames"
    if ($failed) { throw 'A map script failed to compile; see console.log.' }
    if (-not $done) { throw 'Movie did not complete.' }
} finally {
    $assemble = $true
    Get-Process -Name hl2 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe } | Stop-Process
    Copy-Item -LiteralPath (Join-Path $normal 'mapspawn.nut') -Destination (Join-Path $mod 'scripts\vscripts\mapspawn.nut') -Force
    Copy-Item -LiteralPath (Join-Path $normal 'autoexec.cfg') -Destination (Join-Path $mod 'cfg\autoexec.cfg') -Force
    if ($Director -and (Test-Path $directorBackup)) { Copy-Item -LiteralPath $directorBackup -Destination $looseDirector -Force }
    Copy-Item -LiteralPath $log -Destination (Join-Path $movieDir 'console.log') -ErrorAction SilentlyContinue
    'normal runtime restored'
}
& (Join-Path $r10 'assemble_movie.ps1') -Prefix $Prefix -Fps $Fps
