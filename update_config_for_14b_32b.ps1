# 14B/32Bモデル用に設定ファイルを更新するスクリプト

Write-Host "=" * 60
Write-Host "14B/32Bモデル用設定ファイル更新"
Write-Host "=" * 60
Write-Host ""

$configFile = "llm_routing_config_lm_studio.yaml"

Write-Host "[1] 設定ファイルを確認中..." -ForegroundColor Yellow

if (-not (Test-Path $configFile)) {
    Write-Host "   [エラー] 設定ファイルが見つかりません: $configFile" -ForegroundColor Red
    exit 1
}

Write-Host "   [OK] 設定ファイルが見つかりました" -ForegroundColor Green
Write-Host ""

# 現在のモデルを確認
Write-Host "[2] 現在のモデルを確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET -TimeoutSec 3 -ErrorAction Stop
    $models = ($response.Content | ConvertFrom-Json).data
    $availableModels = $models | ForEach-Object { $_.id }
    
    Write-Host "   利用可能なモデル:" -ForegroundColor Cyan
    foreach ($model in $availableModels) {
        Write-Host "     - $model" -ForegroundColor Gray
    }
    
    $has14B = $availableModels | Where-Object { $_ -like "*14b*" -or $_ -like "*14B*" }
    $has32B = $availableModels | Where-Object { $_ -like "*32b*" -or $_ -like "*32B*" }
    
    Write-Host ""
    if ($has14B) {
        Write-Host "   ✅ 14Bモデルが見つかりました: $has14B" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  14Bモデルが見つかりませんでした" -ForegroundColor Yellow
    }
    
    if ($has32B) {
        Write-Host "   ✅ 32Bモデルが見つかりました: $has32B" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  32Bモデルが見つかりませんでした" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "   [エラー] LM Studioサーバーに接続できません" -ForegroundColor Red
    Write-Host "   LM Studioサーバーが起動しているか確認してください" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] 設定ファイルの更新方法:" -ForegroundColor Yellow
Write-Host ""
Write-Host "14Bモデルを追加する場合:" -ForegroundColor Cyan
Write-Host '  difficulty_routing:' -ForegroundColor Gray
Write-Host '    high:' -ForegroundColor Gray
Write-Host '      models:' -ForegroundColor Gray
Write-Host '        primary: "qwen2.5-coder-14b-instruct"' -ForegroundColor Gray
Write-Host '        fallback:' -ForegroundColor Gray
Write-Host '          - "qwen2.5-coder-7b-instruct"' -ForegroundColor Gray
Write-Host ""
Write-Host "32Bモデルを追加する場合:" -ForegroundColor Cyan
Write-Host '  difficulty_routing:' -ForegroundColor Gray
Write-Host '    high:' -ForegroundColor Gray
Write-Host '      models:' -ForegroundColor Gray
Write-Host '        primary: "qwen2.5-coder-32b-instruct"' -ForegroundColor Gray
Write-Host '        fallback:' -ForegroundColor Gray
Write-Host '          - "qwen2.5-coder-14b-instruct"' -ForegroundColor Gray
Write-Host '          - "qwen2.5-coder-7b-instruct"' -ForegroundColor Gray
Write-Host ""
Write-Host "📖 詳細ガイド:" -ForegroundColor Cyan
Write-Host "   ADD_14B_32B_MODELS_STEP_BY_STEP.md を参照してください" -ForegroundColor Gray
Write-Host ""



















