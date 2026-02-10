@echo off
REM 4 API ログオン時自動起動を登録（管理者権限で実行）
cd /d "%~dp0"
powershell -NoProfile -Command "Start-Process pwsh -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0setup_system3_autostart.ps1\"' -Verb RunAs -Wait"
pause
