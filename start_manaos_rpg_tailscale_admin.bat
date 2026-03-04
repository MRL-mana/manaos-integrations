@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process pwsh -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0start_manaos_rpg_tailscale.ps1""'"
