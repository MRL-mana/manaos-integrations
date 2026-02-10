# Pixel 7 ブリッジを自動で Tailscale / USB のどちらかで起動
# Tailscale (100.84.2.125:5555) が使えれば無線、なければ USB
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$PIXEL7_TAILSCALE_IP = if ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } else { "100.84.2.125" }
$PIXEL7_ADB_PORT = if ($env:PIXEL7_ADB_PORT) { $env:PIXEL7_ADB_PORT } else { "5555" }

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5122/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "Pixel 7 ブリッジは既に起動中です (5122)."
    exit 0
} catch {}

# Tailscale 経由で接続を試行
adb connect "${PIXEL7_TAILSCALE_IP}:${PIXEL7_ADB_PORT}" 2>$null
Start-Sleep -Seconds 1
$devices = adb devices
$useTailscale = $devices -match "${PIXEL7_TAILSCALE_IP}:${PIXEL7_ADB_PORT}\s+device"

if ($useTailscale) {
    Write-Host "Tailscale 経由でブリッジを起動します ($PIXEL7_TAILSCALE_IP:$PIXEL7_ADB_PORT)" -ForegroundColor Cyan
    $env:PIXEL7_ADB_SERIAL = "${PIXEL7_TAILSCALE_IP}:${PIXEL7_ADB_PORT}"
}
Start-Process python -ArgumentList "pixel7_adb_bridge.py" -WindowStyle Hidden -WorkingDirectory $scriptDir

Start-Sleep -Seconds 2
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5122/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "Pixel 7 ブリッジを起動しました (http://127.0.0.1:5122)" -ForegroundColor Green
} catch {
    Write-Host "起動を開始しました。数秒後に http://127.0.0.1:5122 で確認してください。" -ForegroundColor Yellow
}
