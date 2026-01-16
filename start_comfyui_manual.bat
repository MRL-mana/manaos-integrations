@echo off
chcp 65001 >nul
cd /d C:\ComfyUI
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1
set PYTHONUTF8=1
python main.py
pause
