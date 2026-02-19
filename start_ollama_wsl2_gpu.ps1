# WSL2環境でOllamaをGPUモードで起動するスクリプト

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "=== WSL2環境でOllamaをGPUモードで起動 ===" -ForegroundColor Cyan

# 1. WSL2の状態確認
Write-Host "`n[1] WSL2の状態確認中..." -ForegroundColor Yellow
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] WSL2が利用可能です" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] WSL2が利用できません" -ForegroundColor Red
    exit 1
}

# 2. GPU認識確認
Write-Host "`n[2] WSL2内でGPU認識確認中..." -ForegroundColor Yellow
$gpuCheck = wsl -d Ubuntu-22.04 -- nvidia-smi --query-gpu=name --format=csv,noheader 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] GPUが認識されています: $gpuCheck" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] GPUが認識されていません" -ForegroundColor Red
    exit 1
}

# 3. 既存のOllamaプロセスを停止
Write-Host "`n[3] 既存のOllamaプロセスを停止中..." -ForegroundColor Yellow
wsl -d Ubuntu-22.04 -- bash -c "pkill ollama || true" 2>&1 | Out-Null
Start-Sleep -Seconds 2
Write-Host "  [OK] 停止しました" -ForegroundColor Green

# 4. 環境変数を設定してOllamaを起動
Write-Host "`n[4] OllamaをGPUモードで起動中..." -ForegroundColor Yellow
$startScript = @"
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_LAYERS=99
export OLLAMA_USE_CUDA=1
export OLLAMA_CUDA=1
export CUDA_VISIBLE_DEVICES=0
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
"@

wsl -d Ubuntu-22.04 -- bash -c $startScript 2>&1 | Out-Null
Start-Sleep -Seconds 3
Write-Host "  [OK] Ollamaを起動しました" -ForegroundColor Green

# 5. 起動確認
Write-Host "`n[5] 起動確認中..." -ForegroundColor Yellow
$apiCheck = wsl -d Ubuntu-22.04 -- bash -c "curl -s http://127.0.0.1:11434/api/tags" 2>&1
if ($LASTEXITCODE -eq 0 -and $apiCheck -match "models") {
    Write-Host "  [OK] Ollamaが正常に起動しています" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Ollamaの起動確認に失敗しました" -ForegroundColor Yellow
    Write-Host "  ログを確認: wsl -d Ubuntu-22.04 -- cat /tmp/ollama.log" -ForegroundColor Cyan
}

# 6. GPU使用状況確認
Write-Host "`n[6] GPU使用状況確認中..." -ForegroundColor Yellow
$gpuUsage = wsl -d Ubuntu-22.04 -- nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>&1
Write-Host "  GPU使用状況: $gpuUsage" -ForegroundColor Green

Write-Host "`n=== 完了 ===" -ForegroundColor Cyan
Write-Host "`n使用方法:" -ForegroundColor Yellow
Write-Host "  WSL2内でモデルを実行: wsl -d Ubuntu-22.04 -- ollama run qwen3:4b 'プロンプト'" -ForegroundColor White
Write-Host "  GPU使用確認: wsl -d Ubuntu-22.04 -- ollama ps" -ForegroundColor White
Write-Host "  Ollama停止: wsl -d Ubuntu-22.04 -- pkill ollama" -ForegroundColor White
Write-Host ""

