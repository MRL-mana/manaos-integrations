# LM Studioサーバー自動起動スクリプト

Write-Host "=" * 60
Write-Host "LM Studioサーバー自動起動"
Write-Host "=" * 60
Write-Host ""

# LM Studioのパス
$lmStudioPath = "C:\Users\mana4\AppData\Local\Programs\LM Studio\LM Studio.exe"

# ステップ1: LM Studioが起動しているか確認
Write-Host "[1] LM Studioプロセスを確認中..." -ForegroundColor Yellow
$lmStudioProcess = Get-Process -Name "LM Studio" -ErrorAction SilentlyContinue
if (-not $lmStudioProcess) {
    Write-Host "   [起動中] LM Studioを起動します..." -ForegroundColor Yellow
    if (Test-Path $lmStudioPath) {
        Start-Process -FilePath $lmStudioPath
        Write-Host "   [✅] LM Studioを起動しました" -ForegroundColor Green
        Write-Host "   起動完了まで待機中..." -ForegroundColor Gray
        Start-Sleep -Seconds 10
    } else {
        Write-Host "   [❌] LM Studioが見つかりませんでした: $lmStudioPath" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   [✅] LM Studioは既に起動しています" -ForegroundColor Green
}

# ステップ2: サーバーが起動しているか確認
Write-Host ""
Write-Host "[2] LM Studioサーバーの状態を確認中..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
$serverStarted = $false

while ($retryCount -lt $maxRetries -and -not $serverStarted) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:1234/v1/models" -Method GET -TimeoutSec 2 -ErrorAction Stop
        $serverStarted = $true
        Write-Host "   [✅] LM Studioサーバーが起動しています！" -ForegroundColor Green
        
        $models = ($response.Content | ConvertFrom-Json).data
        Write-Host "   利用可能なモデル数: $($models.Count)" -ForegroundColor Cyan
        foreach ($model in $models) {
            Write-Host "     - $($model.id)" -ForegroundColor Gray
        }
        break
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            if ($retryCount % 5 -eq 0) {
                Write-Host "   [待機中...] サーバーの起動を待っています ($retryCount/$maxRetries)" -ForegroundColor Yellow
            }
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $serverStarted) {
    Write-Host ""
    Write-Host "   [⚠️] 自動起動できませんでした" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "手動でサーバーを起動してください:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "方法1: LM Studio GUIで起動" -ForegroundColor White
    Write-Host "  1. LM Studioの「Server」タブをクリック" -ForegroundColor Gray
    Write-Host "  2. モデルを選択（ダウンロード済みのモデル）" -ForegroundColor Gray
    Write-Host "  3. 「Start Server」ボタンをクリック" -ForegroundColor Gray
    Write-Host ""
    Write-Host "方法2: ブラウザで確認" -ForegroundColor White
    Write-Host "  LM Studioが起動している場合、以下にアクセス:" -ForegroundColor Gray
    Write-Host "  http://127.0.0.1:1234/v1/models" -ForegroundColor Gray
    Write-Host ""
    Write-Host "確認コマンド:" -ForegroundColor Cyan
    Write-Host "  .\check_running_status.ps1" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "=" * 60
Write-Host "✅ LM Studioサーバーが起動しました！" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "これで完全運用開始です！🎉" -ForegroundColor Green
Write-Host ""
Write-Host "確認:" -ForegroundColor Cyan
Write-Host "  .\check_running_status.ps1" -ForegroundColor Gray
Write-Host ""



















