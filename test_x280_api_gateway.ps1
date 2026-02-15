# X280 API Gateway テストスクリプト
# ローカルでAPI Gatewayを起動してテスト

Write-Host "=== X280 API Gateway テスト ===" -ForegroundColor Cyan

# 1. API Gatewayをバックグラウンドで起動
Write-Host "`n[1] API Gatewayを起動中..." -ForegroundColor Yellow
$env:X280_API_PORT = "5120"
$env:X280_API_HOST = "0.0.0.0"

$job = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    $env:X280_API_PORT = "5120"
    $env:X280_API_HOST = "0.0.0.0"
    python x280_api_gateway.py
}

Start-Sleep -Seconds 5
Write-Host "  [OK] API Gatewayを起動しました（ジョブID: $($job.Id)）" -ForegroundColor Green

# 2. ヘルスチェック
Write-Host "`n[2] ヘルスチェック中..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:5120/api/health" -Method Get -TimeoutSec 5
    Write-Host "  [OK] API Gatewayは正常に動作しています" -ForegroundColor Green
    Write-Host "  ステータス: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "  [ERROR] ヘルスチェックに失敗: $_" -ForegroundColor Red
    Stop-Job $job
    Remove-Job $job
    exit 1
}

# 3. システム情報取得テスト
Write-Host "`n[3] システム情報取得テスト..." -ForegroundColor Yellow
try {
    $sysInfo = Invoke-RestMethod -Uri "http://127.0.0.1:5120/api/system/info" -Method Get -TimeoutSec 10
    Write-Host "  [OK] システム情報を取得しました" -ForegroundColor Green
    Write-Host "  ホスト名: $($sysInfo.hostname)" -ForegroundColor Cyan
} catch {
    Write-Host "  [WARN] システム情報取得に失敗: $_" -ForegroundColor Yellow
}

# 4. リソース情報取得テスト
Write-Host "`n[4] リソース情報取得テスト..." -ForegroundColor Yellow
try {
    $resources = Invoke-RestMethod -Uri "http://127.0.0.1:5120/api/system/resources" -Method Get -TimeoutSec 10
    Write-Host "  [OK] リソース情報を取得しました" -ForegroundColor Green
    Write-Host "  CPU使用率: $($resources.cpu.usage_percent)%" -ForegroundColor Cyan
    Write-Host "  メモリ使用率: $($resources.memory.usage_percent)%" -ForegroundColor Cyan
    Write-Host "  ディスク使用率: $($resources.disk.usage_percent)%" -ForegroundColor Cyan
} catch {
    Write-Host "  [WARN] リソース情報取得に失敗: $_" -ForegroundColor Yellow
}

# 5. コマンド実行テスト
Write-Host "`n[5] コマンド実行テスト..." -ForegroundColor Yellow
try {
    $body = @{
        command = "hostname"
        timeout = 10
    } | ConvertTo-Json
    
    $cmdResult = Invoke-RestMethod -Uri "http://127.0.0.1:5120/api/execute" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
    Write-Host "  [OK] コマンドを実行しました" -ForegroundColor Green
    Write-Host "  コマンド: $($cmdResult.command)" -ForegroundColor Cyan
    Write-Host "  終了コード: $($cmdResult.exit_code)" -ForegroundColor Cyan
    Write-Host "  出力: $($cmdResult.stdout.Trim())" -ForegroundColor Cyan
} catch {
    Write-Host "  [WARN] コマンド実行に失敗: $_" -ForegroundColor Yellow
}

# 6. API Gatewayを停止
Write-Host "`n[6] API Gatewayを停止中..." -ForegroundColor Yellow
Stop-Job $job
Remove-Job $job
Write-Host "  [OK] API Gatewayを停止しました" -ForegroundColor Green

Write-Host "`n=== テスト完了 ===" -ForegroundColor Cyan
Write-Host "`n次のステップ:" -ForegroundColor Yellow
Write-Host "  1. X280側にファイルを転送: scp x280_api_gateway.py x280:C:/manaos_x280/" -ForegroundColor White
Write-Host "  2. X280側で起動: ssh x280 'cd C:/manaos_x280; python x280_api_gateway.py'" -ForegroundColor White
Write-Host ""

