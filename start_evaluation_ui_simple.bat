@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 既存のプロセスを停止中...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *evaluation*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :9600 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 >nul

echo.
echo 画像評価UIを起動します...
echo.
python start_image_evaluation_web.py
