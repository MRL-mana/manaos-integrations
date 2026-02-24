param(
    [string]$ExpectedTailscaleIp = "100.84.2.125",
    [int]$ExpectedAdbPort = 5555
)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Pixel7 ADB Doctor ===" -ForegroundColor Cyan

Write-Host "\n[1/4] adb version" -ForegroundColor Yellow
adb version 2>$null

Write-Host "\n[2/4] Restart adb server" -ForegroundColor Yellow
adb kill-server | Out-Null
adb start-server | Out-Null

Write-Host "\n[3/4] adb devices" -ForegroundColor Yellow
$devicesRaw = adb devices -l 2>$null
if ($devicesRaw) { Write-Host $devicesRaw }

$hasDevice = $false
$hasUnauthorized = $false
$hasOffline = $false
if ($devicesRaw) {
    if ($devicesRaw -match "\sdevice\s*") { $hasDevice = $true }
    if ($devicesRaw -match "\sunauthorized\s*") { $hasUnauthorized = $true }
    if ($devicesRaw -match "\soffline\s*") { $hasOffline = $true }
}

Write-Host "\n[4/4] Windows USB enumeration (Pixel/Android/Google)" -ForegroundColor Yellow
try {
    $hits = Get-PnpDevice -PresentOnly | Where-Object {
        $_.FriendlyName -match 'Android|ADB|Pixel|Google' -or
        $_.InstanceId -match 'VID_18D1|VID_04E8|VID_0BB4'
    } | Select-Object Status,Class,FriendlyName,InstanceId

    if ($hits -and $hits.Count -gt 0) {
        $hits | Format-Table -AutoSize
    } else {
        Write-Host "(no matching USB devices found)" -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "Get-PnpDevice not available in this shell. Skipping USB enumeration." -ForegroundColor DarkYellow
}

Write-Host "\n=== Next steps ===" -ForegroundColor Cyan

if ($hasDevice -and -not $hasUnauthorized) {
    Write-Host "✅ ADB sees a device. Proceed with setup:" -ForegroundColor Green
    Write-Host "  pwsh -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\setup_pixel7_tailscale_adb.ps1" -ForegroundColor White
    Write-Host "  pwsh -NoProfile -ExecutionPolicy Bypass -File .\\pixel7_minimal_quick.ps1 -SkipOpenWebUIStart" -ForegroundColor White
    exit 0
}

if ($hasUnauthorized) {
    Write-Host "⚠️  Device is 'unauthorized'." -ForegroundColor Yellow
    Write-Host "- Pixel 7をロック解除" -ForegroundColor White
    Write-Host "- 『USBデバッグを許可』をOK（常に許可にチェック推奨）" -ForegroundColor White
    Write-Host "- もう一度: adb devices" -ForegroundColor White
    exit 2
}

Write-Host "❌ ADBがPixel 7を検出できていません。" -ForegroundColor Red
Write-Host "まず以下を確認:" -ForegroundColor Yellow
Write-Host "- ケーブルが『データ対応』か（充電専用だとPCに出ません）" -ForegroundColor White
Write-Host "- Pixel側: USBの設定を『ファイル転送(MTP)』に変更" -ForegroundColor White
Write-Host "- Pixel側: 開発者向けオプション > USBデバッグ ON" -ForegroundColor White
Write-Host "- 可能なら別USBポート/別ケーブルで試す" -ForegroundColor White
Write-Host "\nUSBを使わず進めるなら（おすすめ）:" -ForegroundColor Yellow
Write-Host "- Pixel側: 開発者向けオプション > ワイヤレスデバッグ > ペア設定" -ForegroundColor White
Write-Host "- 表示された『ペアリングIP:ポート』『6桁コード』『接続IP:ポート』を教えてください" -ForegroundColor White
Write-Host "  こちらで scripts\\setup_pixel7_wireless_debugging.ps1 相当を一発実行します" -ForegroundColor White
