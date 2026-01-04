@echo off
chcp 65001 >nul
echo ========================================
echo ManaOS統合システム起動
echo ========================================
echo.

cd /d "%~dp0"

echo [起動中] 統合APIサーバー (ポート 9500)...
start "ManaOS Unified API" python unified_api_server.py

timeout /t 2 /nobreak >nul

echo [起動中] リアルタイムダッシュボード (ポート 9600)...
start "ManaOS Realtime Dashboard" python realtime_dashboard.py

timeout /t 2 /nobreak >nul

echo [起動中] マスターコントロールパネル (ポート 9700)...
start "ManaOS Master Control" python master_control.py

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo 起動完了
echo ========================================
echo.
echo 起動中のサービス:
echo   - 統合APIサーバー: http://localhost:9500
echo   - リアルタイムダッシュボード: http://localhost:9600
echo   - マスターコントロールパネル: http://localhost:9700
echo.
echo 各ウィンドウを閉じるか、Ctrl+Cで停止できます。
echo.
pause


















