# ピクセル7ワイヤレスADB接続セットアップスクリプト（Windows版）

Write-Host "📱 ピクセル7ワイヤレスADB接続セットアップを開始します..." -ForegroundColor Cyan

# 設定
$PIXEL7_IP = if ($env:PIXEL7_IP) { $env:PIXEL7_IP } else { "100.127.121.20" }
$PIXEL7_ADB_PORT = if ($env:PIXEL7_ADB_PORT) { $env:PIXEL7_ADB_PORT } else { "5555" }

Write-Host ""
Write-Host "📋 手順1: ピクセル7側の設定" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Gray
Write-Host "1. 設定 > デバイス情報 > ビルド番号を7回タップして開発者オプションを有効化"
Write-Host "2. 設定 > 開発者オプション > USBデバッグを有効化"
Write-Host "3. 設定 > 開発者オプション > ワイヤレスデバッグを有効化"
Write-Host "4. ワイヤレスデバッグをタップして、ポート番号を確認（通常は5桁の数字）"
Write-Host ""
$confirm = Read-Host "ピクセル7側の設定は完了しましたか？ (y/n)"

if ($confirm -ne "y") {
    Write-Host "ピクセル7側の設定を完了してから再度実行してください。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 手順2: ワイヤレスデバッグポートの確認" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Gray
$WIRELESS_PORT = Read-Host "ピクセル7のワイヤレスデバッグポート番号を入力してください（例: 12345）"

if ([string]::IsNullOrWhiteSpace($WIRELESS_PORT)) {
    Write-Host "ポート番号が入力されていません。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 手順3: ADB接続の確認" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Gray

# ADBがインストールされているか確認
try {
    $adbVersion = adb version 2>&1
    Write-Host "ADBバージョン確認:" -ForegroundColor Green
    Write-Host $adbVersion
} catch {
    Write-Host "ADBがインストールされていません。" -ForegroundColor Red
    Write-Host ""
    Write-Host "ADBをインストールする方法:"
    Write-Host "1. Android SDK Platform Toolsをダウンロード:"
    Write-Host "   https://developer.android.com/studio/releases/platform-tools"
    Write-Host "2. ダウンロードしたzipを展開"
    Write-Host "3. 環境変数PATHにadb.exeのパスを追加"
    Write-Host ""
    Write-Host "または、Chocolateyを使用:"
    Write-Host "   choco install adb"
    exit 1
}

Write-Host ""
Write-Host "📋 手順4: ワイヤレスADB接続" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Gray

# 既存の接続を切断
Write-Host "既存の接続を確認中..." -ForegroundColor Gray
adb disconnect "${PIXEL7_IP}:${PIXEL7_ADB_PORT}" 2>$null

# ワイヤレスデバッグポート経由で接続
Write-Host "ワイヤレスデバッグポート経由で接続中..." -ForegroundColor Gray
adb connect "${PIXEL7_IP}:${WIRELESS_PORT}"

Start-Sleep -Seconds 2

# 接続確認
Write-Host ""
Write-Host "接続デバイスを確認中..." -ForegroundColor Gray
adb devices

# 通常のADBポートに切り替え
Write-Host ""
Write-Host "ADB TCP/IPモードに切り替え中..." -ForegroundColor Gray
adb tcpip ${PIXEL7_ADB_PORT}

Start-Sleep -Seconds 2

# 通常ポートで再接続
Write-Host ""
Write-Host "通常ポートで再接続中..." -ForegroundColor Gray
adb disconnect "${PIXEL7_IP}:${WIRELESS_PORT}" 2>$null
adb connect "${PIXEL7_IP}:${PIXEL7_ADB_PORT}"

Start-Sleep -Seconds 2

# 最終確認
Write-Host ""
Write-Host "📋 最終確認" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Gray
$devices = adb devices | Select-String -Pattern "${PIXEL7_IP}:${PIXEL7_ADB_PORT}" | Where-Object { $_ -match "device" }

if ($devices) {
    Write-Host "✅ 接続成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "接続中のデバイス:" -ForegroundColor Gray
    adb devices
    Write-Host ""
    Write-Host "ピクセル7の情報:" -ForegroundColor Gray
    adb shell getprop ro.product.model
    adb shell getprop ro.build.version.release
    Write-Host ""
    Write-Host "🎉 セットアップ完了！" -ForegroundColor Green
    Write-Host ""
    Write-Host "次回からは以下のコマンドで接続できます:" -ForegroundColor Cyan
    Write-Host "  adb connect ${PIXEL7_IP}:${PIXEL7_ADB_PORT}" -ForegroundColor White
} else {
    Write-Host "❌ 接続に失敗しました。" -ForegroundColor Red
    Write-Host ""
    Write-Host "確認事項:" -ForegroundColor Yellow
    Write-Host "1. ピクセル7と母艦が同じTailscaleネットワークに接続されているか"
    Write-Host "2. ピクセル7のワイヤレスデバッグが有効になっているか"
    Write-Host "3. ファイアウォールでポートがブロックされていないか"
    exit 1
}

