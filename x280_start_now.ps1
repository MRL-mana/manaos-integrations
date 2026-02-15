# X280 API Gateway - Start Now Script
# This script starts the API Gateway immediately on X280

$ErrorActionPreference = "Stop"

Write-Host "=== Starting X280 API Gateway Now ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = "C:\manaos_x280"
if (-not (Test-Path $scriptDir)) {
    Write-Host "ERROR: Directory not found: $scriptDir" -ForegroundColor Red
    exit 1
}
Set-Location $scriptDir

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    exit 1
}

# Check if API Gateway script exists
Write-Host "[2/4] Checking API Gateway script..." -ForegroundColor Yellow
$apiScript = Join-Path $scriptDir "x280_api_gateway.py"
if (-not (Test-Path $apiScript)) {
    Write-Host "[ERROR] x280_api_gateway.py not found" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] API Gateway script found" -ForegroundColor Green

$x280Port = if ($env:X280_API_PORT) { [int]$env:X280_API_PORT } else { 5120 }

# Stop existing process on port
Write-Host "[3/4] Checking port $x280Port..." -ForegroundColor Yellow
$existingConnections = Get-NetTCPConnection -LocalPort $x280Port -ErrorAction SilentlyContinue
if ($existingConnections) {
    $processes = $existingConnections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $processes) {
        Write-Host "  Stopping process (PID: $procId)..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}
Write-Host "[OK] Port $x280Port is available" -ForegroundColor Green

# Set environment variables
Write-Host "[4/4] Starting API Gateway..." -ForegroundColor Yellow
$env:X280_API_PORT = "$x280Port"
$env:X280_API_HOST = "0.0.0.0"

# Start API Gateway in a new window (so we can see it)
Write-Host "Starting API Gateway..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:X280_API_PORT='$x280Port'; `$env:X280_API_HOST='0.0.0.0'; python x280_api_gateway.py"

Start-Sleep -Seconds 5

# Check if it's running
Write-Host ""
Write-Host "Checking API Gateway status..." -ForegroundColor Yellow
$x280ApiBaseUrl = if ($env:X280_API_URL) {
    $env:X280_API_URL.TrimEnd('/')
} else {
    "http://127.0.0.1:$x280Port"
}
try {
    $response = Invoke-RestMethod -Uri "$x280ApiBaseUrl/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] API Gateway is running!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
    Write-Host "  Port: $x280Port" -ForegroundColor Cyan
    Write-Host "  Documentation: $x280ApiBaseUrl/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The API Gateway window is open. Keep it running." -ForegroundColor Yellow
} catch {
    Write-Host "[WARNING] API Gateway may not be running yet" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Yellow
    Write-Host "  Please check the PowerShell window that opened" -ForegroundColor Yellow
}


















