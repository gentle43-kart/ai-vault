@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
set "URL=%~1"
if "!URL!"=="" set /p "URL=YouTube URL (paste and press Enter): "
if "!URL!"=="" goto :eof
py -3.12 video_to_script.py "!URL!" %2 %3 %4 %5 %6
echo.
echo Output folder: %~dp0output
pause
