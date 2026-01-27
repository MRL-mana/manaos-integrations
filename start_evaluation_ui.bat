@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 画像評価UIを起動します...
echo.
python start_image_evaluation_web.py
pause
