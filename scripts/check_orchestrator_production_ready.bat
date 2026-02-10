@echo off
REM ask_orchestrator 本格運用の起動確認（5106 + Portal + 集計）
cd /d "%~dp0\.."
python scripts\check_orchestrator_production_ready.py
exit /b %ERRORLEVEL%
