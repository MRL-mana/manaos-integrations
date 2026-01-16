@echo off
chcp 65001 >nul
echo ComfyUIを再起動します...
echo.
echo 既存のComfyUIプロセスを終了中...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ComfyUI*" >nul 2>&1
timeout /t 2 >nul
echo.
echo 環境変数を設定してComfyUIを起動します...
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1
cd C:\ComfyUI
start "ComfyUI" python main.py
echo.
echo ComfyUIを起動しました。
echo 数秒待ってから画像生成を再試行してください。
pause
