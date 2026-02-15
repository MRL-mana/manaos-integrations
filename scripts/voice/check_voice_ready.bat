@echo off
REM 音声運用開始可否チェック
cd /d "%~dp0\..\.."
python scripts\voice\check_voice_ready.py --base http://127.0.0.1:9510 %*
exit /b %errorlevel%
