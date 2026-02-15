# 14B/32Bモデル用設定を適用するスクリプト

Write-Host "=" * 60
Write-Host "14B/32Bモデル用設定の適用"
Write-Host "=" * 60
Write-Host ""

# LM Studio API base URL（env優先、/v1吸収）
$lmStudioRawUrl = if ($env:LM_STUDIO_URL) { $env:LM_STUDIO_URL.TrimEnd('/') } else { "http://127.0.0.1:1234" }
$lmStudioApiBaseUrl = if ($lmStudioRawUrl -match "/v1$") { $lmStudioRawUrl } else { "$lmStudioRawUrl/v1" }

# 現在のモデルを確認
Write-Host "[1] 現在のモデルを確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$lmStudioApiBaseUrl/models" -Method GET -TimeoutSec 3 -ErrorAction Stop
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
        Write-Host "   ✅ 14Bモデルが見つかりました" -ForegroundColor Green
        $use14B = $true
    } else {
        Write-Host "   ⚠️  14Bモデルが見つかりませんでした" -ForegroundColor Yellow
        $use14B = $false
    }
    
    if ($has32B) {
        Write-Host "   ✅ 32Bモデルが見つかりました" -ForegroundColor Green
        $use32B = $true
    } else {
        Write-Host "   ⚠️  32Bモデルが見つかりませんでした" -ForegroundColor Yellow
        $use32B = $false
    }
    
} catch {
    Write-Host "   [エラー] LM Studioサーバーに接続できません" -ForegroundColor Red
    Write-Host "   LM Studioサーバーが起動しているか確認してください" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2] 設定ファイルを更新しますか？" -ForegroundColor Cyan
Write-Host ""

if ($use32B) {
    Write-Host "   32Bモデルが見つかりました" -ForegroundColor Green
    Write-Host "   32Bモデル用設定を適用しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
    $apply32B = Read-Host
    if ($apply32B -eq "y" -or $apply32B -eq "Y") {
        Copy-Item -Path "llm_routing_config_lm_studio_with_32b.yaml" -Destination "llm_routing_config_lm_studio.yaml" -Force
        Write-Host "   [✅] 32Bモデル用設定を適用しました" -ForegroundColor Green
        exit 0
    }
}

if ($use14B) {
    Write-Host "   14Bモデルが見つかりました" -ForegroundColor Green
    Write-Host "   14Bモデル用設定を適用しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
    $apply14B = Read-Host
    if ($apply14B -eq "y" -or $apply14B -eq "Y") {
        Copy-Item -Path "llm_routing_config_lm_studio_with_14b.yaml" -Destination "llm_routing_config_lm_studio.yaml" -Force
        Write-Host "   [✅] 14Bモデル用設定を適用しました" -ForegroundColor Green
        exit 0
    }
}

if (-not $use14B -and -not $use32B) {
    Write-Host "   ⚠️  14B/32Bモデルが見つかりませんでした" -ForegroundColor Yellow
    Write-Host "   まずLM Studioでモデルをダウンロードしてください" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   手順:" -ForegroundColor Cyan
    Write-Host "   1. LM Studioの「Search」タブで「Qwen2.5-Coder-14B-Instruct」を検索" -ForegroundColor White
    Write-Host "   2. モデルをダウンロード" -ForegroundColor White
    Write-Host "   3. 「Server」タブでモデルを読み込む" -ForegroundColor White
    Write-Host "   4. このスクリプトを再実行" -ForegroundColor White
}

Write-Host ""
Write-Host "=" * 60
Write-Host "設定の適用をスキップしました" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""



















