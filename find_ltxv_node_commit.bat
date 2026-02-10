@echo off
REM ComfyUI-LTXVideo で LTXVSeparateAVLatent があったコミットを検索
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_ltxv_node_commit.ps1" %*
exit /b %ERRORLEVEL%
