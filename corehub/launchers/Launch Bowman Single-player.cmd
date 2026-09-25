@echo off
cd /d "%~dp0"
start "" "%~dp0hl2.wrap.exe" -game bowman_singleplayer -tempcontent -insecure -corehubvr -windowed -w 1280 -h 720 -novid -condebug +mat_queue_mode 0 +maxplayers 1
