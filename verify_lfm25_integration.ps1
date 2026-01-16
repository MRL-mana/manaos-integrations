# LFM 2.5統合効果確認スクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LFM 2.5統合効果確認" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "[1] サービス状態確認..." -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="Intent Router"; Port=5100},
    @{Name="Task Planner"; Port=5101},
    @{Name="Content Generation"; Port=5109},
    @{Name="Unified API Server"; Port=9500}
)

$allRunning = $true

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✓ $($service.Name): 動作中" -ForegroundColor Green
    } catch {
        $portCheck = Test-NetConnection -ComputerName localhost -Port $service.Port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($portCheck) {
            Write-Host "  ⚠ $($service.Name): ポートは開いています" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ $($service.Name): 停止中" -ForegroundColor Red
            $allRunning = $false
        }
    }
}

Write-Host ""
Write-Host "[2] LFM 2.5統合テスト実行..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path "test_lfm25_integration.py") {
    Write-Host "  テストスクリプトを実行中..." -ForegroundColor Cyan
    python test_lfm25_integration.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  ✓ テスト成功" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "  ⚠ テストに一部失敗がありました（詳細は上記を確認）" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ test_lfm25_integration.py が見つかりません" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] 簡単な動作確認..." -ForegroundColor Yellow
Write-Host ""

# Intent Routerの簡単なテスト
try {
    $testData = @{
        text = "こんにちは"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "http://localhost:5100/api/classify" -Method Post -Body $testData -ContentType "application/json" -TimeoutSec 5
    
    Write-Host "  ✓ Intent Router: 動作確認成功" -ForegroundColor Green
    Write-Host "    意図タイプ: $($response.intent_type)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Intent Router: 動作確認失敗" -ForegroundColor Red
    Write-Host "    エラー: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "確認完了" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "期待される効果:" -ForegroundColor Cyan
Write-Host "  - Intent Router: レイテンシ70-90%削減" -ForegroundColor Yellow
Write-Host "  - Secretary Routines: レイテンシ80-85%削減" -ForegroundColor Yellow
Write-Host "  - Task Planner: 簡単な計画で80-85%削減" -ForegroundColor Yellow
Write-Host "  - Content Generation: 下書き生成で80-85%削減" -ForegroundColor Yellow
Write-Host ""
