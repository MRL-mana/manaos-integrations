@echo off
title ManaOS - デバイス用クイック起動 (3/6)
cd /d "%~dp0"
call powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0quick_start_devices.ps1"
echo.
pause
