# 3/6 オンラインをワンクリックで（Pixel 7 ブリッジ + Unified Orchestrator 5106）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "=== デバイス用クイック起動 (3/6 オンライン) ===" -ForegroundColor Cyan
Write-Host ""

& "$scriptDir\start_pixel7_bridge.ps1"
Start-Sleep -Seconds 1
& "$scriptDir\start_orchestrator_5106.ps1"

Write-Host ""
Write-Host "デバイス確認: .\scripts\check_devices_online.ps1" -ForegroundColor Gray
Write-Host "MCP: device_discover / pixel7_* が使えます。" -ForegroundColor Gray
