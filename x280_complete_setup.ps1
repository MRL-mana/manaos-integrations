# X280 API Gateway Complete Setup and Start
# This script ensures all dependencies are installed and starts the API Gateway

$ErrorActionPreference = "Continue"

Write-Host "=== X280 API Gateway Complete Setup ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = "C:\manaos_x280"
if (-not (Test-Path $scriptDir)) {
    Write-Host "ERROR: Directory not found: $scriptDir" -ForegroundColor Red
    Write-Host "Creating directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null
}
Set-Location $scriptDir

# 1. Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    exit 1
}

# 2. Install/Upgrade pip
Write-Host "[2/5] Ensuring pip is up to date..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null
Write-Host "[OK] pip ready" -ForegroundColor Green

# 3. Install required packages
Write-Host "[3/5] Installing required packages..." -ForegroundColor Yellow
$requiredPackages = @("fastapi", "uvicorn[standard]", "httpx", "pydantic")
foreach ($package in $requiredPackages) {
    Write-Host "  Installing $package..." -ForegroundColor Cyan
    python -m pip install $package --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $package" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $package installation may have issues" -ForegroundColor Yellow
    }
}

# 4. Check if API Gateway script exists
Write-Host "[4/5] Checking API Gateway script..." -ForegroundColor Yellow
$apiScript = Join-Path $scriptDir "x280_api_gateway.py"
if (-not (Test-Path $apiScript)) {
    Write-Host "[ERROR] x280_api_gateway.py not found" -ForegroundColor Red
    Write-Host "Please transfer the file to X280" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] API Gateway script found" -ForegroundColor Green

# 5. Stop existing processes
Write-Host "[5/5] Checking for existing processes..." -ForegroundColor Yellow
try {
    $existingConnections = netstat -ano | Select-String ":5120" | Select-String "LISTENING"
    if ($existingConnections) {
        $pids = $existingConnections | ForEach-Object {
            ($_ -split '\s+')[-1]
        } | Select-Object -Unique
        foreach ($pid in $pids) {
            Write-Host "  Stopping process (PID: $pid)..." -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "  [INFO] Could not check for existing processes" -ForegroundColor Gray
}
Write-Host "[OK] Ready to start" -ForegroundColor Green

# 6. Set environment variables and start
Write-Host ""
Write-Host "Starting X280 API Gateway..." -ForegroundColor Cyan
$env:X280_API_PORT = "5120"
$env:X280_API_HOST = "0.0.0.0"

# Start API Gateway
Write-Host "Running: python x280_api_gateway.py" -ForegroundColor Yellow
Write-Host "Host: 0.0.0.0" -ForegroundColor Gray
Write-Host "Port: 5120" -ForegroundColor Gray
Write-Host ""

# Start in background using Start-Process
$process = Start-Process python -ArgumentList "x280_api_gateway.py" -PassThru -WindowStyle Hidden -WorkingDirectory $scriptDir

Write-Host "API Gateway process started (PID: $($process.Id))" -ForegroundColor Green
Write-Host "Waiting for startup..." -ForegroundColor Yellow

# Wait and check
Start-Sleep -Seconds 8

# Check if it's running
Write-Host ""
Write-Host "Checking API Gateway status..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5120/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] API Gateway is running!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
    Write-Host "  Process ID: $($process.Id)" -ForegroundColor Cyan
    Write-Host "  Port: 5120" -ForegroundColor Cyan
    Write-Host "  Documentation: http://localhost:5120/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To check from remote:" -ForegroundColor Yellow
    Write-Host "  http://100.127.121.20:5120/api/health" -ForegroundColor Cyan
} catch {
    Write-Host "[WARNING] Could not verify API Gateway status" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Yellow
    Write-Host "  Process ID: $($process.Id)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please check manually:" -ForegroundColor Yellow
    Write-Host "  1. Check if process is running: Get-Process -Id $($process.Id)" -ForegroundColor Gray
    Write-Host "  2. Check port: netstat -ano | findstr :5120" -ForegroundColor Gray
    Write-Host "  3. Check logs if available" -ForegroundColor Gray
}


















