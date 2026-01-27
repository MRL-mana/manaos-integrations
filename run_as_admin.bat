@echo off
REM 管理者権限でPowerShellスクリプトを実行するバッチファイル

echo ========================================
echo 管理者権限でComfyUI削除スクリプトを実行
echo ========================================
echo.

REM 管理者権限でPowerShellを起動
powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0remove_comfyui_admin.ps1\"'"

pause
