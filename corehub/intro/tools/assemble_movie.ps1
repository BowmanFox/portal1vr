# Turns a recorded test run (r10\record_movie.ps1) into videos and stills:
#   r10\videos\<Prefix>_map.mp4   full-size rebuild with in-game audio
#   r10\videos\<Prefix>_side.mp4  original video | rebuild, in-game audio
#   r10\stills\<Prefix>\a###.jpg / b###.jpg  frames at t=s and s+0.5 for scoring
param([Parameter(Mandatory = $true)][string]$Prefix, [int]$Fps = 60)
$ErrorActionPreference = 'Stop'
$ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if (-not $ff) { $ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName }
if (-not $ff) { throw 'ffmpeg not found' }
$r10 = $PSScriptRoot
$work = Split-Path -Parent $r10
$M = Join-Path $work "runtime\game\corehub_intro\movies\$Prefix"
$O = Join-Path $r10 'videos'
$stillDir = Join-Path $r10 "stills\$Prefix"
New-Item -ItemType Directory -Force $O, $stillDir | Out-Null
$ref = Join-Path $r10 'ref\p2_intro.bik'
$refStills = Join-Path $r10 'ref\stills'
if (-not (Test-Path (Join-Path $refStills 'r0267.jpg'))) {
    New-Item -ItemType Directory -Force $refStills | Out-Null
    & $ff -y -hide_banner -loglevel error -i $ref -vf 'fps=2:round=near,scale=640:360' -q:v 3 -start_number 0 (Join-Path $refStills 'r%04d.jpg')
}
$font = "fontfile='C\:/Windows/Fonts/arialbd.ttf'"
& $ff -y -hide_banner -loglevel error -framerate $Fps -i "$M\f%04d.jpg" -i "$M\f.wav" `
    -vf 'scale=1280:720:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 19 `
    -c:a aac -b:a 192k -shortest (Join-Path $O "$($Prefix)_map.mp4")
$fc = "[0:v]setpts=N/(30000/1001)/TB,fps=$Fps,scale=960:540,drawtext=$($font):text='Original 2009 video':x=12:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5[a];" +
      "[1:v]scale=960:540:flags=lanczos,drawtext=$($font):text='Rebuild test run':x=12:y=10:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.5," +
      "drawtext=$($font):text='%{pts\:hms}':x=w-tw-12:y=10:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5[b];[a][b]hstack=inputs=2,format=yuv420p[v]"
& $ff -y -hide_banner -loglevel error -i $ref -framerate $Fps -i "$M\f%04d.jpg" -i "$M\f.wav" `
    -filter_complex $fc -map '[v]' -map '2:a' -c:v libx264 -preset medium -crf 21 -c:a aac -b:a 160k -shortest (Join-Path $O "$($Prefix)_side.mp4")
$n = (Get-ChildItem -LiteralPath $M -Filter '*.jpg').Count
for ($sec = 0; $sec -le 134; $sec++) {
    foreach ($pair in @(@('a', $sec), @('b', ($sec + 0.5)))) {
        $i = [int][math]::Round($pair[1] * $Fps)
        if ($i -lt $n) { Copy-Item -LiteralPath (Join-Path $M ('f{0:D4}.jpg' -f $i)) -Destination (Join-Path $stillDir ('{0}{1:D3}.jpg' -f $pair[0], $sec)) -Force }
    }
}
"assembled $Prefix frames=$n"
