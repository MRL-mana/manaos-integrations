@echo off
cd /d "%~dp0"
echo Starting Evaluation UI on http://127.0.0.1:9601
echo Keep this window open. Close it to stop the server.
echo.
python -u scripts\lifecycle\start_evaluation_ui_port9601.py
pause
