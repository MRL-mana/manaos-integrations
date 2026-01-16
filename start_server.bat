@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo ManaOS統合APIサーバー起動
echo ============================================================
echo.
python start_server_direct.py
pause








