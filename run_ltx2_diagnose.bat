@echo off
REM LTX-2 一括診断（接続・ノード一覧・互換ワークフロー）
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_ltx2_diagnose.ps1" %*
exit /b %ERRORLEVEL%
