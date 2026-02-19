# Step-Deep-Research サービス起動スクリプト

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "Step-Deep-Research サービス起動中..." -ForegroundColor Cyan

$service = @{
    Name = "Step Deep Research"
    Port = 5121
    Script = "step_deep_research_service.py"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "step_deep_research_service.log"
$errorLogFile = Join-Path $logDir "step_deep_research_service_error.log"

Write-Host "サービス: $($service.Name)" -ForegroundColor Yellow
Write-Host "ポート: $($service.Port)" -ForegroundColor Yellow
Write-Host "スクリプト: $($service.Script)" -ForegroundColor Yellow
Write-Host "ログ: $logFile" -ForegroundColor Yellow

# Pythonスクリプトを起動
$pythonScript = Join-Path $scriptDir $service.Script

if (-not (Test-Path $pythonScript)) {
    Write-Host "❌ スクリプトが見つかりません: $pythonScript" -ForegroundColor Red
    exit 1
}

# ポートチェック
$portInUse = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️  ポート $($service.Port) は既に使用されています" -ForegroundColor Yellow
    Write-Host "   既存のプロセスを停止しますか？ (Y/N)"
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        $process = Get-Process -Id $portInUse.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $process.Id -Force
            Write-Host "✅ プロセスを停止しました" -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
    } else {
        Write-Host "❌ 起動をキャンセルしました" -ForegroundColor Red
        exit 1
    }
}

# サービス起動
Write-Host "`n🚀 サービスを起動しています..." -ForegroundColor Green

try {
    $process = Start-Process python -ArgumentList $pythonScript -NoNewWindow -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile
    
    Write-Host "✅ サービス起動完了 (PID: $($process.Id))" -ForegroundColor Green
    Write-Host "`nサービス情報:" -ForegroundColor Cyan
    Write-Host "  - 名前: $($service.Name)" -ForegroundColor White
    Write-Host "  - ポート: $($service.Port)" -ForegroundColor White
    Write-Host "  - URL: http://127.0.0.1:$($service.Port)" -ForegroundColor White
    Write-Host "  - PID: $($process.Id)" -ForegroundColor White
    Write-Host "  - ログ: $logFile" -ForegroundColor White
    
    Write-Host "`n📝 ログを確認するには:" -ForegroundColor Cyan
    Write-Host "  Get-Content $logFile -Wait" -ForegroundColor White
    
    Write-Host "`n🛑 停止するには:" -ForegroundColor Cyan
    Write-Host "  Stop-Process -Id $($process.Id)" -ForegroundColor White
    
} catch {
    Write-Host "❌ サービス起動エラー: $_" -ForegroundColor Red
    exit 1
}



