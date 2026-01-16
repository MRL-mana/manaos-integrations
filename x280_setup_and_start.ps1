# X280 API Gateway Setup and Start Script
# This script installs dependencies and starts the API Gateway on X280

$ErrorActionPreference = "Stop"

Write-Host "=== X280 API Gateway Setup and Start ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = "C:\manaos_x280"
if (-not (Test-Path $scriptDir)) {
    Write-Host "ERROR: Directory not found: $scriptDir" -ForegroundColor Red
    exit 1
}
Set-Location $scriptDir

# 1. Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    exit 1
}

# 2. Install required packages
Write-Host "[2/4] Installing required packages..." -ForegroundColor Yellow
$requiredPackages = @("fastapi", "uvicorn", "httpx", "pydantic")
foreach ($package in $requiredPackages) {
    Write-Host "  Installing $package..." -ForegroundColor Cyan
    pip install $package --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $package installed" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Failed to install $package" -ForegroundColor Yellow
    }
}

# 3. Check if API Gateway script exists
Write-Host "[3/4] Checking API Gateway script..." -ForegroundColor Yellow
$apiScript = Join-Path $scriptDir "x280_api_gateway.py"
if (-not (Test-Path $apiScript)) {
    Write-Host "[ERROR] x280_api_gateway.py not found" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] API Gateway script found" -ForegroundColor Green

# 4. Stop existing process on port 5120
Write-Host "[4/4] Checking port 5120..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort 5120 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcess) {
    Write-Host "  Stopping existing process (PID: $existingProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $existingProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Write-Host "[OK] Port 5120 is available" -ForegroundColor Green

# 5. Set environment variables and start API Gateway
Write-Host ""
Write-Host "Starting X280 API Gateway..." -ForegroundColor Cyan
$env:X280_API_PORT = "5120"
$env:X280_API_HOST = "0.0.0.0"

# Start API Gateway in background
$process = Start-Process python -ArgumentList $apiScript -PassThru -WindowStyle Hidden
Write-Host "API Gateway process started (PID: $($process.Id))" -ForegroundColor Green

# Wait for startup
Start-Sleep -Seconds 5

# Check if it's running
Write-Host ""
Write-Host "Checking API Gateway status..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5120/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] API Gateway is running!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
    Write-Host "  Port: 5120" -ForegroundColor Cyan
    Write-Host "  Documentation: http://localhost:5120/docs" -ForegroundColor Cyan
} catch {
    Write-Host "[WARNING] API Gateway may not be running yet" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Yellow
    Write-Host "  Process ID: $($process.Id)" -ForegroundColor Yellow
    Write-Host "  Please check the process manually" -ForegroundColor Yellow
}



















