# ピクセル7ワイヤレスADB接続スクリプト（簡易版・Windows版）

$PIXEL7_IP = if ($env:PIXEL7_IP) { $env:PIXEL7_IP } else { "100.127.121.20" }
$PIXEL7_ADB_PORT = if ($env:PIXEL7_ADB_PORT) { $env:PIXEL7_ADB_PORT } else { "5555" }

Write-Host "📱 ピクセル7に接続中..." -ForegroundColor Cyan

# 接続試行
adb connect "${PIXEL7_IP}:${PIXEL7_ADB_PORT}"

Start-Sleep -Seconds 2

# 接続確認
$devices = adb devices | Select-String -Pattern "${PIXEL7_IP}:${PIXEL7_ADB_PORT}" | Where-Object { $_ -match "device" }

if ($devices) {
    Write-Host "✅ 接続成功！" -ForegroundColor Green
    adb devices
} else {
    Write-Host "❌ 接続失敗。以下を確認してください:" -ForegroundColor Red
    Write-Host "1. ピクセル7のワイヤレスデバッグが有効か"
    Write-Host "2. 同じTailscaleネットワークに接続されているか"
    Write-Host "3. 初回接続の場合は setup_pixel7_adb.ps1 を実行してください"
}

