@echo off
rem 국회 관심 법률안 모니터링 웹 화면 실행 (브라우저: http://localhost:8000)
cd /d "%~dp0"
start "" http://localhost:8000
".venv\Scripts\python.exe" -m app.cli serve --port 8000
