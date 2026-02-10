@echo off
REM 音声運用開始可否チェック
cd /d "%~dp0\..\.."
python scripts\voice\check_voice_ready.py --base http://localhost:9500 %*
exit /b %errorlevel%
