@echo off
chcp 65001 >nul
py -3.12 "%~dp0hwp_to_pdf.py" %*
echo.
pause
