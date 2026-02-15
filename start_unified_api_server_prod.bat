@echo off
setlocal

REM Safe defaults for production
if "%MANAOS_INTEGRATION_HOST%"=="" set MANAOS_INTEGRATION_HOST=127.0.0.1
if "%MANAOS_INTEGRATION_PORT%"=="" set MANAOS_INTEGRATION_PORT=9510
if "%MANAOS_DEBUG%"=="" set MANAOS_DEBUG=false

python run_unified_api_server_prod.py

endlocal

