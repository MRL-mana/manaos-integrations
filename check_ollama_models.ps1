# Ollamaモデル確認スクリプト

Write-Host "=== Ollamaモデル使用状況 ===" -ForegroundColor Cyan
Write-Host ""

# インストール済みモデル一覧
Write-Host "[1] インストール済みモデル一覧" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    $tags = $response.Content | ConvertFrom-Json
    if ($tags.models) {
        Write-Host ""
        foreach ($model in $tags.models) {
            $sizeGB = [math]::Round($model.size / 1GB, 2)
            Write-Host "  - $($model.name) ($sizeGB GB)" -ForegroundColor Green
        }
    } else {
        Write-Host "  モデルが見つかりません" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Ollama APIに接続できません: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[2] 実行中のモデル（メモリにロード済み）" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/ps" -UseBasicParsing -TimeoutSec 5
    $processes = $response.Content | ConvertFrom-Json
    if ($processes.processes -and $processes.processes.Count -gt 0) {
        Write-Host ""
        foreach ($proc in $processes.processes) {
            $memMB = [math]::Round($proc.size / 1MB, 2)
            Write-Host "  - $($proc.model) (メモリ: $memMB MB)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  現在メモリにロードされているモデルはありません" -ForegroundColor Gray
        Write-Host "  （使用時に自動的にロードされます）" -ForegroundColor Gray
    }
} catch {
    Write-Host "  実行中モデルの取得に失敗しました" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] ManaOSでのモデル使用設定" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Intent Router: llama3.2:3b (意図分類)" -ForegroundColor Green
Write-Host "  Task Planner: llama3.2:3b (実行計画作成)" -ForegroundColor Green
Write-Host "  Task Critic: llama3.2:3b (結果評価)" -ForegroundColor Green
Write-Host "  RAG Memory: qwen2.5:14b (重要度スコア計算)" -ForegroundColor Green
Write-Host "  Content Generation: qwen2.5:14b (成果物自動生成)" -ForegroundColor Green
Write-Host "  LLM最適化: 動的モデル管理" -ForegroundColor Green
Write-Host "    - フィルタ: llama3.2:1b (超軽量)" -ForegroundColor Gray
Write-Host "    - 会話: llama3.2:3b (軽量)" -ForegroundColor Gray
Write-Host "    - 判断: qwen2.5:14b (中型)" -ForegroundColor Gray
Write-Host "    - 生成: qwen2.5:32b (大型、必要時のみ)" -ForegroundColor Gray

Write-Host ""
Write-Host "[4] モデルロード方式" -ForegroundColor Yellow
Write-Host "  Ollamaは動的モデル管理を使用しています:" -ForegroundColor Gray
Write-Host "  - 使用時に自動的にモデルをロード" -ForegroundColor Gray
Write-Host "  - 300秒間未使用のモデルは自動アンロード" -ForegroundColor Gray
Write-Host "  - 最大2つのモデルを同時にメモリに保持" -ForegroundColor Gray
Write-Host "  - VRAM使用率80%を超えると自動的にアンロード" -ForegroundColor Gray

Write-Host ""

