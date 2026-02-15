# LM Studioサーバー起動スクリプト

Write-Host "=" * 60
Write-Host "LM Studioサーバー起動"
Write-Host "=" * 60
Write-Host ""

# LM Studioのパスを検索
$lmStudioPaths = @(
    "$env:LOCALAPPDATA\Programs\LM Studio\LM Studio.exe",
    "C:\Users\$env:USERNAME\AppData\Local\Programs\LM Studio\LM Studio.exe",
    "C:\Program Files\LM Studio\LM Studio.exe"
)

$lmStudioExe = $null
foreach ($path in $lmStudioPaths) {
    if (Test-Path $path) {
        $lmStudioExe = $path
        Write-Host "[OK] LM Studioが見つかりました: $path" -ForegroundColor Green
        break
    }
}

if (-not $lmStudioExe) {
    Write-Host "[警告] LM Studioが見つかりませんでした" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "手動で起動してください:" -ForegroundColor Cyan
    Write-Host "  1. LM Studioを起動" -ForegroundColor White
    Write-Host "  2. 「Server」タブでモデルを選択" -ForegroundColor White
    Write-Host "  3. 「Start Server」をクリック" -ForegroundColor White
    Write-Host ""
    Write-Host "または、LM Studioのインストールパスを指定してください:" -ForegroundColor Cyan
    Write-Host "  .\start_lm_studio_server.ps1 -Path 'C:\Path\To\LM Studio.exe'" -ForegroundColor Gray
    exit 1
}

# LM Studioが既に起動しているか確認
$lmStudioProcess = Get-Process -Name "LM Studio" -ErrorAction SilentlyContinue
if ($lmStudioProcess) {
    Write-Host "[情報] LM Studioは既に起動しています" -ForegroundColor Yellow
    Write-Host "   PID: $($lmStudioProcess.Id)" -ForegroundColor Gray
} else {
    Write-Host "[1] LM Studioを起動中..." -ForegroundColor Yellow
    Start-Process -FilePath $lmStudioExe
    Write-Host "   [OK] LM Studioを起動しました" -ForegroundColor Green
    Write-Host "   サーバーを開始するまで待機してください..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "[2] LM Studioサーバーの状態を確認中..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$maxRetries = 10
$retryCount = 0
$serverStarted = $false

while ($retryCount -lt $maxRetries -and -not $serverStarted) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:1234/v1/models" -Method GET -TimeoutSec 2 -ErrorAction Stop
        $serverStarted = $true
        Write-Host "   [OK] LM Studioサーバーが起動しています！" -ForegroundColor Green
        
        $models = ($response.Content | ConvertFrom-Json).data
        Write-Host "   利用可能なモデル数: $($models.Count)" -ForegroundColor Cyan
        foreach ($model in $models) {
            Write-Host "     - $($model.id)" -ForegroundColor Gray
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "   [待機中...] サーバーの起動を待っています ($retryCount/$maxRetries)" -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        } else {
            Write-Host "   [警告] LM Studioサーバーに接続できません" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "   手動でサーバーを起動してください:" -ForegroundColor Cyan
            Write-Host "     1. LM Studioの「Server」タブを開く" -ForegroundColor White
            Write-Host "     2. モデルを選択" -ForegroundColor White
            Write-Host "     3. 「Start Server」をクリック" -ForegroundColor White
            Write-Host ""
            Write-Host "   確認: .\check_running_status.ps1" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "=" * 60
if ($serverStarted) {
    Write-Host "✅ LM Studioサーバーが起動しました！" -ForegroundColor Green
    Write-Host ""
    Write-Host "これで完全運用開始です！🎉" -ForegroundColor Green
} else {
    Write-Host "⚠️  LM Studioサーバーの起動を確認できませんでした" -ForegroundColor Yellow
    Write-Host "   手動でサーバーを起動してください" -ForegroundColor Gray
}
Write-Host "=" * 60
Write-Host ""



















