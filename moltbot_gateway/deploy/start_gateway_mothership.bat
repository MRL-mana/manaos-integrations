@echo off
REM 母艦で MoltBot Gateway を起動（8088）。秘書ファイル整理・MCP moltbot_* を使う前に実行。
cd /d "%~dp0..\.."
if not defined MOLTBOT_GATEWAY_DATA_DIR set MOLTBOT_GATEWAY_DATA_DIR=%CD%\moltbot_gateway_data
if not defined MOLTBOT_GATEWAY_SECRET set MOLTBOT_GATEWAY_SECRET=local_secret
if not defined EXECUTOR set EXECUTOR=mock
echo MoltBot Gateway (port 8088) starting...
echo .env に MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088 と MOLTBOT_GATEWAY_SECRET=local_secret を設定すると統合API/MCP から利用できます。
python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088
pause
