@echo off
setlocal

REM Stable Diffusion prompt generator (Windows cmd wrapper)
REM Usage:
REM   sd-prompt "猫がベッドで寝ている"
REM   sd-prompt -Model llama3-uncensored "美しい夕日と海"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sd-prompt.ps1" %*

endlocal
