@echo off
REM 統合API (9502) と MoltBot Gateway (8088) の疎通確認
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_manaos_stack.ps1"
pause
