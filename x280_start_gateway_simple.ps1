# X280 API Gateway Simple Start Script
# Run this on X280 to start the API Gateway

$ErrorActionPreference = "Stop"

Write-Host "Starting X280 API Gateway..." -ForegroundColor Cyan

# Change to script directory
$scriptDir = "C:\manaos_x280"
if (-not (Test-Path $scriptDir)) {
    Write-Host "ERROR: Directory not found: $scriptDir" -ForegroundColor Red
    exit 1
}
Set-Location $scriptDir

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Check if API Gateway script exists
$apiScript = Join-Path $scriptDir "x280_api_gateway.py"
if (-not (Test-Path $apiScript)) {
    Write-Host "ERROR: x280_api_gateway.py not found" -ForegroundColor Red
    exit 1
}

# Set environment variables
$env:X280_API_PORT = "5120"
$env:X280_HOST = "0.0.0.0"

# Start API Gateway in background
Write-Host "Starting API Gateway on port 5120..." -ForegroundColor Yellow
Start-Process python -ArgumentList $apiScript -WindowStyle Hidden

Start-Sleep -Seconds 3

# Check if it's running
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5120/api/health" -TimeoutSec 5
    Write-Host "SUCCESS: API Gateway is running!" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "WARNING: API Gateway may not be running yet" -ForegroundColor Yellow
    Write-Host "Error: $_" -ForegroundColor Yellow
}



















