# OllamaをGPUモードで実行するための設定

Write-Host "Ollama GPU設定を確認・修正します..." -ForegroundColor Cyan

# 環境変数を設定
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
Write-Host "[OK] 環境変数を設定: OLLAMA_NUM_GPU=1, OLLAMA_GPU_LAYERS=99" -ForegroundColor Green

# Ollamaプロセスを確認
Write-Host "`nOllamaプロセス:" -ForegroundColor Yellow
ollama ps

# GPU使用をテスト
Write-Host "`nGPU使用をテスト中..." -ForegroundColor Yellow
$testResult = curl -X POST http://localhost:11434/api/generate `
  -H "Content-Type: application/json" `
  -d '{\"model\": \"qwen2.5:7b\", \"prompt\": \"test\", \"options\": {\"num_gpu\": 99}, \"stream\": false}' 2>$null

if ($testResult) {
    Write-Host "[OK] テスト成功" -ForegroundColor Green
} else {
    Write-Host "[ERROR] テスト失敗" -ForegroundColor Red
}

# GPU使用率を確認
Write-Host "`nGPU使用率:" -ForegroundColor Yellow
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>$null

Write-Host "`n完了" -ForegroundColor Cyan



