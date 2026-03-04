@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process pwsh -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0start_tailscale_full_stack.ps1""'"
