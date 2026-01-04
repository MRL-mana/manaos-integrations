# OllamaをGPUモードで起動するスクリプト（最終版）

Write-Host "OllamaをGPUモードで起動します..." -ForegroundColor Cyan

# 1. Ollamaを完全に停止
Write-Host "`n[1] Ollamaを停止中..." -ForegroundColor Yellow
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
Write-Host "  [OK] Ollamaを停止しました" -ForegroundColor Green

# 2. 環境変数を設定（セッション用）
Write-Host "`n[2] 環境変数を設定中..." -ForegroundColor Yellow
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
$env:OLLAMA_USE_CUDA = 1
$env:OLLAMA_CUDA = 1
# CUDA_VISIBLE_DEVICESを設定（GPU 0を使用）
$env:CUDA_VISIBLE_DEVICES = "0"
Write-Host "  OLLAMA_NUM_GPU = $env:OLLAMA_NUM_GPU" -ForegroundColor Green
Write-Host "  OLLAMA_GPU_LAYERS = $env:OLLAMA_GPU_LAYERS" -ForegroundColor Green
Write-Host "  OLLAMA_USE_CUDA = $env:OLLAMA_USE_CUDA" -ForegroundColor Green
Write-Host "  OLLAMA_CUDA = $env:OLLAMA_CUDA" -ForegroundColor Green
Write-Host "  CUDA_VISIBLE_DEVICES = $env:CUDA_VISIBLE_DEVICES" -ForegroundColor Green

# 3. ユーザー環境変数として永続化
Write-Host "`n[3] 環境変数を永続化中..." -ForegroundColor Yellow
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_LAYERS", "99", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_USE_CUDA", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_CUDA", "1", "User")
[System.Environment]::SetEnvironmentVariable("CUDA_VISIBLE_DEVICES", "0", "User")
Write-Host "  [OK] 環境変数を永続化しました" -ForegroundColor Green

# 4. Ollamaを起動（環境変数を設定した状態で）
Write-Host "`n[4] Ollamaを起動中..." -ForegroundColor Yellow
# 環境変数を再設定
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
$env:OLLAMA_USE_CUDA = 1
$env:OLLAMA_CUDA = 1
$env:CUDA_VISIBLE_DEVICES = "0"

# 新しいプロセスで環境変数を設定して起動
Start-Process -FilePath "ollama" -WindowStyle Hidden -Environment @{
    "OLLAMA_NUM_GPU" = "1"
    "OLLAMA_GPU_LAYERS" = "99"
    "OLLAMA_USE_CUDA" = "1"
    "OLLAMA_CUDA" = "1"
    "CUDA_VISIBLE_DEVICES" = "0"
}
Start-Sleep -Seconds 5
Write-Host "  [OK] Ollamaを起動しました" -ForegroundColor Green

# 5. 起動確認
Write-Host "`n[5] 起動確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 10
    if ($response.models) {
        Write-Host "  [OK] Ollamaが正常に起動しました" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] モデルが見つかりません" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Ollamaの起動確認に失敗しました: $_" -ForegroundColor Red
}

# 6. GPU使用状況を確認
Write-Host "`n[6] GPU使用状況を確認中..." -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>$null
    Write-Host "  GPU使用率: $gpuInfo" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] GPU情報の取得に失敗しました" -ForegroundColor Yellow
}

# 7. ollama psで確認
Write-Host "`n[7] Ollamaプロセス確認中..." -ForegroundColor Yellow
try {
    $ollamaPs = ollama ps 2>$null
    Write-Host "  $ollamaPs" -ForegroundColor Green
    if ($ollamaPs -match "100% CPU") {
        Write-Host "  [WARN] CPUモードで実行されています" -ForegroundColor Yellow
    } elseif ($ollamaPs -match "GPU") {
        Write-Host "  [OK] GPUモードで実行されています" -ForegroundColor Green
    }
} catch {
    Write-Host "  [INFO] モデルがロードされていません" -ForegroundColor Cyan
}

Write-Host "`n完了しました！" -ForegroundColor Cyan
Write-Host "`n注意: 環境変数は新しいプロセスにのみ適用されます。" -ForegroundColor Yellow
Write-Host "Ollamaを再起動した後、`ollama ps`でGPUモードになっているか確認してください。" -ForegroundColor Yellow



