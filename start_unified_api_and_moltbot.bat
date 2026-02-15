@echo off
REM 統合API (9502) と MoltBot Gateway (8088) をまとめて起動。MCP・秘書ファイル整理を利用するとき用。
cd /d "%~dp0"

echo [1/2] 統合API (9502) を起動します...
start "Unified API 9502" cmd /k "cd /d %~dp0 && set PORT=9502 && python unified_api_server.py"

echo 少し待ってから MoltBot Gateway を起動します...
timeout /t 5 /nobreak >nul

echo [2/2] MoltBot Gateway (8088) を起動します...
if not defined MOLTBOT_GATEWAY_DATA_DIR set MOLTBOT_GATEWAY_DATA_DIR=%~dp0moltbot_gateway_data
if not defined MOLTBOT_GATEWAY_SECRET set MOLTBOT_GATEWAY_SECRET=local_secret
if not defined EXECUTOR set EXECUTOR=mock
start "MoltBot Gateway 8088" cmd /k "cd /d %~dp0 && set MOLTBOT_GATEWAY_DATA_DIR=%~dp0moltbot_gateway_data && set MOLTBOT_GATEWAY_SECRET=local_secret && set EXECUTOR=mock && python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088"

echo.
echo 起動しました。
echo   統合API:     http://127.0.0.1:9502
echo   MoltBot:    http://127.0.0.1:8088  (秘書ファイル整理用)
echo .env に MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088 があると MCP から利用できます。
pause
