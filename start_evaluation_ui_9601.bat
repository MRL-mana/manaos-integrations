@echo off
cd /d "%~dp0"
echo Starting Evaluation UI on http://localhost:9601
echo Keep this window open. Close it to stop the server.
echo.
python -u start_evaluation_ui_port9601.py
pause
