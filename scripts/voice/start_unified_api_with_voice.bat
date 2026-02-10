@echo off
REM 統合APIを音声機能付きで起動する前の案内
cd /d "%~dp0\..\.."

echo ========================================
echo  音声付き 統合API 起動
echo ========================================
echo.
echo 1. VOICEVOX を起動してください（未起動の場合）
echo    - デフォルト: http://127.0.0.1:50021
echo.
echo 2. 統合APIを起動します...
echo    python unified_api_server.py
echo.
pause

python unified_api_server.py
pause
