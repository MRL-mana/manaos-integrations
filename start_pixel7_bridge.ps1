# Pixel 7 ADB ブリッジ起動（母艦で 5122 を立て、USB 接続の Pixel 7 に ADB で転送）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 既に 5122 で応答があれば起動しない
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5122/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "Pixel 7 ブリッジは既に起動中です (5122)."
    exit 0
} catch {}

Start-Process python -ArgumentList "pixel7_adb_bridge.py" -WindowStyle Hidden -WorkingDirectory $scriptDir
Start-Sleep -Seconds 2
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:5122/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "Pixel 7 ブリッジを起動しました (http://127.0.0.1:5122)"
} catch {
    Write-Host "起動を開始しました。数秒後に http://127.0.0.1:5122 で確認してください。"
}
