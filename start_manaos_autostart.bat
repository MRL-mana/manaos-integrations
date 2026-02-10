@echo off
REM ManaOS Auto-startup Batch Script - Silent Mode
REM Completely hidden execution

cd /d "C:\Users\mana4\Desktop\manaos_integrations"
if not exist "logs" mkdir logs

REM Log only the start time
(echo [%date% %time%] ManaOS auto-startup initiated) >> logs\autostart.log

REM Start services completely hidden (no window, no wait, no output from batch itself)
REM Using start /B /MIN to ensure background execution
start /B /MIN "" "C:\Users\mana4\Desktop\.venv\Scripts\python.exe" start_vscode_cursor_services.py

REM Exit immediately - batch script itself doesn't show
exit /b 0
