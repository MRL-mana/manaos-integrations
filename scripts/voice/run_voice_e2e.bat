@echo off
REM 音声API E2Eテスト実行（運用開始確認用）
cd /d "%~dp0\..\.."
echo Running voice E2E test...
python scripts\voice\test_voice_e2e.py --base http://127.0.0.1:9510 %*
if errorlevel 1 exit /b 1
echo E2E finished.
exit /b 0
