# OllamaをGPUモードで再起動するスクリプト（完全版）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ollama GPUモード再起動スクリプト" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Ollamaを完全に停止
Write-Host "`n[1/6] Ollamaを停止中..." -ForegroundColor Yellow
$processes = Get-Process ollama -ErrorAction SilentlyContinue
if ($processes) {
    $processes | Stop-Process -Force
    Write-Host "  [OK] Ollamaプロセスを停止しました ($($processes.Count)個)" -ForegroundColor Green
    Start-Sleep -Seconds 3
} else {
    Write-Host "  [INFO] Ollamaプロセスは見つかりませんでした" -ForegroundColor Cyan
}

# 2. 環境変数を設定（セッション用）
Write-Host "`n[2/6] 環境変数を設定中（セッション用）..." -ForegroundColor Yellow
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
Write-Host "  OLLAMA_NUM_GPU = $env:OLLAMA_NUM_GPU" -ForegroundColor Green
Write-Host "  OLLAMA_GPU_LAYERS = $env:OLLAMA_GPU_LAYERS" -ForegroundColor Green

# 3. ユーザー環境変数として永続化
Write-Host "`n[3/6] 環境変数を永続化中..." -ForegroundColor Yellow
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_LAYERS", "99", "User")
Write-Host "  [OK] 環境変数をユーザー環境変数として設定しました" -ForegroundColor Green

# 4. Ollamaを起動（環境変数を設定してから）
Write-Host "`n[4/6] OllamaをGPUモードで起動中..." -ForegroundColor Yellow
$env:OLLAMA_NUM_GPU = 1
$env:OLLAMA_GPU_LAYERS = 99
Start-Process ollama -WindowStyle Hidden
Start-Sleep -Seconds 5
Write-Host "  [OK] Ollamaを起動しました" -ForegroundColor Green

# 5. 起動確認
Write-Host "`n[5/6] 起動確認中..." -ForegroundColor Yellow
$maxRetries = 10
$retryCount = 0
$started = $false

while ($retryCount -lt $maxRetries -and -not $started) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($response.models) {
            Write-Host "  [OK] Ollamaが正常に起動しました" -ForegroundColor Green
            $started = $true
        } else {
            Write-Host "  [WARN] モデルが見つかりません（リトライ $retryCount/$maxRetries）" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            $retryCount++
        }
    } catch {
        Write-Host "  [INFO] 起動待機中... ($retryCount/$maxRetries)" -ForegroundColor Cyan
        Start-Sleep -Seconds 2
        $retryCount++
    }
}

if (-not $started) {
    Write-Host "  [ERROR] Ollamaの起動確認に失敗しました" -ForegroundColor Red
}

# 6. GPU使用状況を確認
Write-Host "`n[6/6] GPU使用状況を確認中..." -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>$null
    if ($gpuInfo) {
        $parts = $gpuInfo.Split(',')
        Write-Host "  GPU使用率: $($parts[0].Trim())" -ForegroundColor Green
        Write-Host "  VRAM使用量: $($parts[1].Trim()) / $($parts[2].Trim())" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] GPU情報の取得に失敗しました" -ForegroundColor Yellow
}

# 7. ollama psで確認
Write-Host "`n[追加確認] Ollamaプロセス確認..." -ForegroundColor Yellow
try {
    $ollamaPs = ollama ps 2>$null
    if ($ollamaPs) {
        Write-Host "  $ollamaPs" -ForegroundColor Green
        if ($ollamaPs -match "100% CPU") {
            Write-Host "  [WARN] CPUモードで実行されています" -ForegroundColor Yellow
            Write-Host "  [INFO] 実際にLLMを呼び出すとGPUモードになる可能性があります" -ForegroundColor Cyan
        } elseif ($ollamaPs -match "GPU") {
            Write-Host "  [OK] GPUモードで実行されています" -ForegroundColor Green
        }
    } else {
        Write-Host "  [INFO] モデルがまだロードされていません" -ForegroundColor Cyan
        Write-Host "  [INFO] 実際にLLMを呼び出すとモデルがロードされます" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  [INFO] ollama psの実行に失敗しました" -ForegroundColor Cyan
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "完了しました！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n次のステップ:" -ForegroundColor Yellow
Write-Host "  1. 実際にLLMを呼び出してGPU使用を確認" -ForegroundColor White
Write-Host "  2. `ollama ps`でGPUモードになっているか確認" -ForegroundColor White
Write-Host "  3. `nvidia-smi`でGPU使用率を確認" -ForegroundColor White



