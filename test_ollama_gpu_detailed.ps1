# Ollama GPU使用状況の詳細確認スクリプト

Write-Host "=== Ollama GPU使用状況の詳細確認 ===" -ForegroundColor Cyan

# 1. 環境変数の確認
Write-Host "`n[1] 環境変数の確認" -ForegroundColor Yellow
Write-Host "  OLLAMA_NUM_GPU: $env:OLLAMA_NUM_GPU"
Write-Host "  OLLAMA_GPU_LAYERS: $env:OLLAMA_GPU_LAYERS"
Write-Host "  OLLAMA_USE_CUDA: $env:OLLAMA_USE_CUDA"
Write-Host "  CUDA_VISIBLE_DEVICES: $env:CUDA_VISIBLE_DEVICES"

# 2. GPU情報の確認
Write-Host "`n[2] GPU情報の確認" -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=name,driver_version,cuda_version --format=csv,noheader
    Write-Host "  $gpuInfo" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] GPU情報の取得に失敗: $_" -ForegroundColor Red
}

# 3. PyTorch CUDA確認
Write-Host "`n[3] PyTorch CUDA確認" -ForegroundColor Yellow
try {
    $torchInfo = python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); print(f'GPU count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')"
    Write-Host "  $torchInfo" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] PyTorch確認に失敗: $_" -ForegroundColor Red
}

# 4. Ollamaプロセスの確認
Write-Host "`n[4] Ollamaプロセスの確認" -ForegroundColor Yellow
$ollamaProcesses = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollamaProcesses) {
    foreach ($proc in $ollamaProcesses) {
        Write-Host "  PID: $($proc.Id), Path: $($proc.Path)" -ForegroundColor Green
        # 環境変数を確認（管理者権限が必要な場合あり）
        try {
            $envVars = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)" | Select-Object -ExpandProperty CommandLine
            Write-Host "    CommandLine: $envVars" -ForegroundColor Cyan
        } catch {
            Write-Host "    [INFO] 環境変数の取得には管理者権限が必要です" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [INFO] Ollamaプロセスが見つかりません" -ForegroundColor Yellow
}

# 5. Ollama APIでモデル情報を取得
Write-Host "`n[5] Ollama APIでモデル情報を取得" -ForegroundColor Yellow
try {
    $models = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 10
    if ($models.models -and $models.models.Count -gt 0) {
        $firstModel = $models.models[0]
        Write-Host "  モデル: $($firstModel.name)" -ForegroundColor Green
        
        # モデルの詳細情報を取得
        $modelInfo = Invoke-RestMethod -Uri "http://localhost:11434/api/show" -Method Post -Body (@{name=$firstModel.name} | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 10
        Write-Host "  モデル情報取得成功" -ForegroundColor Green
        # GPU関連の情報があれば表示
        if ($modelInfo.details) {
            Write-Host "  詳細情報: $($modelInfo.details | ConvertTo-Json -Depth 3)" -ForegroundColor Cyan
        }
    }
} catch {
    Write-Host "  [ERROR] API呼び出しに失敗: $_" -ForegroundColor Red
}

# 6. ollama psで確認
Write-Host "`n[6] ollama psで確認" -ForegroundColor Yellow
try {
    $ollamaPs = ollama ps 2>&1
    Write-Host "  $ollamaPs" -ForegroundColor Green
    if ($ollamaPs -match "100% CPU") {
        Write-Host "  [WARN] CPUモードで実行されています" -ForegroundColor Yellow
    } elseif ($ollamaPs -match "GPU") {
        Write-Host "  [OK] GPUモードで実行されています" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] モデルがロードされていません" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  [ERROR] ollama psの実行に失敗: $_" -ForegroundColor Red
}

# 7. GPU使用率の確認
Write-Host "`n[7] GPU使用率の確認" -ForegroundColor Yellow
try {
    $gpuUsage = nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
    Write-Host "  GPU使用状況: $gpuUsage" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] GPU使用率の取得に失敗: $_" -ForegroundColor Red
}

Write-Host "`n=== 確認完了 ===" -ForegroundColor Cyan

