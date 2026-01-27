@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 画像評価UI (ポート9601) を起動します...
echo.
python start_evaluation_ui_port9601.py
pause
