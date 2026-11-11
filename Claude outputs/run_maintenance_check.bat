@echo off
rem run_maintenance_check.bat v1.1 (2026-11-11, Claude). ASCII-only comments on purpose: cmd misparses Korean text before chcp.
rem Windows Task Scheduler job "AI-jaryo-jeonggi-jeomgeom" (weekly Wed 09:40) runs maintenance_check.py. See AGENTS_procedure 6.8 stage A.
rem Output (in J:\MCP\ai-vault-mcp\data\maintenance): DATE_check.json, DATE_summary.md, run_history.log ("time exitcode" per run).
rem PY is the same as in run_index_on_request.bat.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "PY=C:\Program Files\Python312\python.exe"
set "OUT=J:\MCP\ai-vault-mcp\data\maintenance"
if not exist "%OUT%" mkdir "%OUT%"
"%PY%" "%~dp0maintenance_check.py" >"%OUT%\last_run.log" 2>&1
set RC=%ERRORLEVEL%
for /f "delims=" %%t in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do >>"%OUT%\run_history.log" echo %%t %RC%
exit /b %RC%
