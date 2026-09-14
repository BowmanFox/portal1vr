@echo off
setlocal
set "PORTAL_VR_DIR=%~dp0"
if not exist "%PORTAL_VR_DIR%hl2.exe" set "PORTAL_VR_DIR=%ProgramFiles(x86)%\Steam\steamapps\common\Portal\"
if not exist "%PORTAL_VR_DIR%hl2.exe" (
  echo Put this launcher beside Portal's hl2.exe.
  pause
  exit /b 1
)
cd /d "%PORTAL_VR_DIR%"
start "" "%PORTAL_VR_DIR%hl2.exe" -game portal -insecure -windowed -novid -w 1280 -h 720 +mat_queue_mode 0 +mat_vsync 0 +mat_antialias 0
