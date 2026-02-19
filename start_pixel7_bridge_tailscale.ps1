# Pixel 7 ADB ブリッジを Tailscale 経由（無線）で使う
# 初回: scripts\setup_pixel7_wireless_debugging.ps1（再起動後も再接続可能）
# または: scripts\setup_pixel7_tailscale_adb.ps1（USB で1回だけ tcpip 有効化）
Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$PIXEL7_TAILSCALE_IP = if ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } else { "100.84.2.125" }
$PIXEL7_ADB_PORT = if ($env:PIXEL7_ADB_PORT) { $env:PIXEL7_ADB_PORT } else { "5555" }
$env:PIXEL7_ADB_SERIAL = "${PIXEL7_TAILSCALE_IP}:${PIXEL7_ADB_PORT}"

# 毎回接続を試行（Wireless debugging なら再起動後もここで接続できる）
adb connect "${PIXEL7_TAILSCALE_IP}:${PIXEL7_ADB_PORT}" 2>$null
Start-Sleep -Seconds 1

Write-Host "Pixel 7 ブリッジ (Tailscale 経由: $env:PIXEL7_ADB_SERIAL)" -ForegroundColor Cyan
& "$scriptDir\start_pixel7_bridge.ps1"
