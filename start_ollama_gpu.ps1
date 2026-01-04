# Ollama GPU Mode Startup Script (WSL2)

Write-Host "=== Ollama GPU Mode Startup (WSL2) ===" -ForegroundColor Cyan

# 1. Check WSL2 status
Write-Host "`n[1/6] Checking WSL2 status..." -ForegroundColor Yellow
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] WSL2 is available" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] WSL2 is not available" -ForegroundColor Red
    exit 1
}

# 2. Check GPU recognition
Write-Host "`n[2/6] Checking GPU recognition in WSL2..." -ForegroundColor Yellow
$gpuCheck = wsl -d Ubuntu-22.04 -- nvidia-smi --query-gpu=name --format=csv,noheader 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] GPU is recognized: $gpuCheck" -ForegroundColor Green
} else {
    Write-Host "  [WARN] GPU is not recognized (will run in CPU mode)" -ForegroundColor Yellow
}

# 3. Stop Windows Ollama (to avoid conflicts)
Write-Host "`n[3/6] Stopping Windows Ollama..." -ForegroundColor Yellow
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force 2>&1 | Out-Null
Start-Sleep -Seconds 2
Write-Host "  [OK] Stopped" -ForegroundColor Green

# 4. Stop existing Ollama processes in WSL2
Write-Host "`n[4/6] Stopping existing Ollama processes in WSL2..." -ForegroundColor Yellow
wsl -d Ubuntu-22.04 -- bash -c "pkill ollama || true" 2>&1 | Out-Null
Start-Sleep -Seconds 2
Write-Host "  [OK] Stopped" -ForegroundColor Green

# 5. Start Ollama in GPU mode in WSL2
Write-Host "`n[5/6] Starting Ollama in GPU mode in WSL2..." -ForegroundColor Yellow
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
Write-Host "  [OK] Ollama started" -ForegroundColor Green

# 6. Verify startup and check GPU usage
Write-Host "`n[6/6] Verifying startup and checking GPU usage..." -ForegroundColor Yellow
try {
    $apiCheck = wsl -d Ubuntu-22.04 -- bash -c "curl -s http://localhost:11434/api/tags" 2>&1
    if ($LASTEXITCODE -eq 0 -and $apiCheck -match "models") {
        Write-Host "  [OK] Ollama is running normally" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Failed to verify Ollama startup" -ForegroundColor Yellow
        Write-Host "  Check logs: wsl -d Ubuntu-22.04 -- cat /tmp/ollama.log" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  [WARN] Failed to verify startup" -ForegroundColor Yellow
}

# Check GPU usage
Write-Host "`nGPU Usage:" -ForegroundColor Cyan
try {
    $gpuUsage = wsl -d Ubuntu-22.04 -- nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>&1
    Write-Host "  $gpuUsage" -ForegroundColor Green
} catch {
    Write-Host "  [INFO] Skipped GPU info retrieval" -ForegroundColor Cyan
}

Write-Host "`n=== Complete ===" -ForegroundColor Cyan
Write-Host "`nUsage:" -ForegroundColor Yellow
Write-Host "  Python: from local_llm_helper import ask; ask('question', 'qwen3:4b')" -ForegroundColor White
Write-Host "  Check GPU: wsl -d Ubuntu-22.04 -- ollama ps" -ForegroundColor White
Write-Host "  Stop Ollama: wsl -d Ubuntu-22.04 -- pkill ollama" -ForegroundColor White
Write-Host ""
