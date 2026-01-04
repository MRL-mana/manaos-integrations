# n8nサーバーの状態を確認するスクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8nサーバー 状態確認" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$n8nUrl = "http://100.93.120.33:5678"

# 1. Healthzエンドポイントの確認
Write-Host "[1/4] Healthzエンドポイントを確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$n8nUrl/healthz" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Healthzエンドポイントは応答しています" -ForegroundColor Green
        Write-Host "  ステータス: $($response.Content)" -ForegroundColor Gray
    }
} catch {
    Write-Host "[NG] Healthzエンドポイントに接続できません: $_" -ForegroundColor Red
}

Write-Host ""

# 2. メインエンドポイントの確認
Write-Host "[2/4] メインエンドポイントを確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $n8nUrl -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] メインエンドポイントは応答しています" -ForegroundColor Green
        Write-Host "  ステータスコード: $($response.StatusCode)" -ForegroundColor Gray
        Write-Host "  コンテンツタイプ: $($response.Headers.'Content-Type')" -ForegroundColor Gray
    }
} catch {
    Write-Host "[NG] メインエンドポイントに接続できません: $_" -ForegroundColor Red
    Write-Host "  エラー詳細: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""

# 3. APIエンドポイントの確認
Write-Host "[3/4] APIエンドポイントを確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$n8nUrl/api/v1/workflows" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] APIエンドポイントは応答しています" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "[OK] APIエンドポイントは応答しています（認証が必要）" -ForegroundColor Green
    } else {
        Write-Host "[NG] APIエンドポイントに接続できません: $_" -ForegroundColor Red
    }
}

Write-Host ""

# 4. このはサーバーでのn8nコンテナの状態確認（SSH経由）
Write-Host "[4/4] このはサーバーでのn8nコンテナの状態を確認中..." -ForegroundColor Yellow
Write-Host "  (SSH接続が必要です)" -ForegroundColor Gray
Write-Host ""
Write-Host "このはサーバーで以下のコマンドを実行してください:" -ForegroundColor Yellow
Write-Host "  ssh konoha" -ForegroundColor White
Write-Host "  docker ps | grep n8n" -ForegroundColor White
Write-Host "  docker logs trinity-n8n --tail 50" -ForegroundColor White

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "確認完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[推奨アクション]" -ForegroundColor Cyan
Write-Host "1. このはサーバーでn8nコンテナが起動しているか確認" -ForegroundColor White
Write-Host "2. n8nコンテナが停止している場合は起動:" -ForegroundColor White
Write-Host "   docker start trinity-n8n" -ForegroundColor Gray
Write-Host "3. ログを確認してエラーがないか確認:" -ForegroundColor White
Write-Host "   docker logs trinity-n8n --tail 100" -ForegroundColor Gray
















