# Pushes the current Corehub intro rebuild (r10) into the Portal 1 VR repo (BowmanFox/portal1vr) as branch
# corehub-intro: a separate git worktree (r10\p1vr-intro) based on the local corehub branch, so the main
# portal1vr checkout is never touched. Files go to corehub/intro/. No BSP (over GitHub's 100 MB limit) and no
# videos (history bloat); small review sheets are included. Run by push_loop.ps1 every 30 minutes.
param([string]$Branch = 'corehub-intro', [string]$Build = '', [string]$Director = '', [switch]$NoPush)
$ErrorActionPreference = 'Stop'
$r10 = $PSScriptRoot
$work = Split-Path -Parent $r10
$wt = Join-Path $r10 'p1vr-intro'
if (-not (Test-Path (Join-Path $wt '.git'))) { throw "worktree $wt is missing" }
# Default to whatever is currently published in outputs\Corehub-Intro (build name and the director with the same hash).
$published = Join-Path (Resolve-Path (Join-Path $r10 '..\..\..')).Path 'outputs\Corehub-Intro'
$ver = Get-Content -LiteralPath (Join-Path $published 'Rebuild-verification.json') -Raw | ConvertFrom-Json
if (-not $Build) { $Build = $ver.compile.geometryCompileRevision }
if (-not $Director) {
    $Director = Get-ChildItem (Join-Path $r10 'build') -Filter 'director_*.nut' | Where-Object { (Get-FileHash $_.FullName).Hash -eq $ver.directorSha256 } |
        Sort-Object LastWriteTime | Select-Object -Last 1 | ForEach-Object { $_.BaseName }
}
if (-not $Build -or -not $Director) { throw "Could not work out the published build/director ($Build / $Director)." }
"build $Build, director $Director"
$dst = Join-Path $wt 'corehub\intro'
foreach ($d in 'map', 'tools', 'models', 'review') { New-Item -ItemType Directory -Force (Join-Path $dst $d) | Out-Null }
Copy-Item (Join-Path $r10 "build\$Build.vmf") (Join-Path $dst 'map\corehub_intro.vmf') -Force
Copy-Item (Join-Path $r10 "build\$Director.nut") (Join-Path $dst 'map\director.nut') -Force
foreach ($f in 'patch_r10.py','patch_director.py','record_movie.ps1','assemble_movie.ps1','push_github.ps1','push_loop.ps1','autostart.ps1','publish_r10.py') {
    Copy-Item (Join-Path $r10 $f) (Join-Path $dst ('tools\' + $f)) -Force }
Copy-Item (Join-Path $r10 'tools\*.py') (Join-Path $dst 'tools') -Force
Copy-Item (Join-Path $work 'watcher.ps1') (Join-Path $dst 'tools\watcher.ps1') -Force
foreach ($f in 'build_board.py', 'scanner_board.qc', 'scanner_board.smd') { Copy-Item (Join-Path $r10 "models\$f") (Join-Path $dst "models\$f") -Force }
Copy-Item (Join-Path $r10 'STATUS.md') (Join-Path $dst 'README.md') -Force
if (Test-Path (Join-Path $r10 'review')) { Copy-Item (Join-Path $r10 'review\*') (Join-Path $dst 'review') -Force }
$lock = New-Object System.Threading.Mutex($false, 'CorehubR10GitPush')
[void]$lock.WaitOne()
Push-Location $wt
$ErrorActionPreference = 'Continue'   # git writes progress to stderr
try {
    $cur = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($cur -ne $Branch) { throw "worktree is on $cur, expected $Branch" }
    git add -A -- corehub/intro
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) { 'no changes since the last commit' } else {
        git -c user.name='Niko (via Claude)' -c user.email='awesomeguy3612@gmail.com' commit -q -m "Corehub intro rebuild ($Build + $Director)" -m "Separated middle rooms, frontal walls, WIP surfaces, 60 fps test runs; see corehub/intro/README.md for per-scene scores." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_014AMsH7FRGKMAJSenMpS1Ga"
        git log --oneline -1
    }
    # Pushing needs the user's explicit go-ahead, recorded as r10\PUSH_APPROVED; until then this only commits locally.
    if ($NoPush -or -not (Test-Path (Join-Path $r10 'PUSH_APPROVED'))) { 'COMMITTED (no push: PUSH_APPROVED not set)'; return }
    $env:GIT_TERMINAL_PROMPT = '0'; $env:GCM_INTERACTIVE = 'never'
    cmd /c "git push -u origin HEAD:refs/heads/$Branch 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "git push failed ($LASTEXITCODE)" }
    "PUSHED $Branch to $((git remote get-url origin).Trim())"
} finally { Pop-Location; $lock.ReleaseMutex() }
