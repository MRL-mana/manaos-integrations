# X280 API Gateway Restart with Firewall Check
# This script restarts the API Gateway and attempts to configure firewall

$ErrorActionPreference = "Continue"

Write-Host "=== X280 API Gateway Restart ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = "C:\manaos_x280"
Set-Location $scriptDir

# Stop existing processes
Write-Host "[1/4] Stopping existing processes..." -ForegroundColor Yellow
try {
    $x280Port = if ($env:X280_API_PORT) { [int]$env:X280_API_PORT } else { 5120 }
    $existingConnections = netstat -ano | Select-String ":$x280Port" | Select-String "LISTENING"
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
Write-Host "[OK] Processes stopped" -ForegroundColor Green

# Check firewall rule
Write-Host "[2/4] Checking firewall rule..." -ForegroundColor Yellow
$firewallRule = netsh advfirewall firewall show rule name="ManaOS X280 API Gateway" 2>&1
if ($LASTEXITCODE -ne 0 -or $firewallRule -match "指定された規則が見つかりません") {
    Write-Host "  [WARN] Firewall rule not found" -ForegroundColor Yellow
    Write-Host "  [INFO] Attempting to create firewall rule..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Please run as Administrator:" -ForegroundColor Yellow
    Write-Host "  netsh advfirewall firewall add rule name=`"ManaOS X280 API Gateway`" dir=in action=allow protocol=TCP localport=$x280Port" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[OK] Firewall rule exists" -ForegroundColor Green
}

# Set environment variables
Write-Host "[3/4] Setting environment variables..." -ForegroundColor Yellow
$env:X280_API_PORT = "$x280Port"
$env:X280_API_HOST = "0.0.0.0"
Write-Host "[OK] Environment variables set" -ForegroundColor Green
Write-Host "  X280_API_PORT = $env:X280_API_PORT" -ForegroundColor Gray
Write-Host "  X280_API_HOST = $env:X280_API_HOST" -ForegroundColor Gray

# Start API Gateway
Write-Host "[4/4] Starting API Gateway..." -ForegroundColor Yellow
$env:X280_API_PORT = "$x280Port"
$env:X280_API_HOST = "0.0.0.0"
$process = Start-Process python -ArgumentList "x280_api_gateway.py" -PassThru -WindowStyle Hidden -WorkingDirectory $scriptDir

Write-Host "API Gateway process started (PID: $($process.Id))" -ForegroundColor Green
Write-Host "Waiting for startup..." -ForegroundColor Yellow

Start-Sleep -Seconds 8

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
    Write-Host "  Process ID: $($process.Id)" -ForegroundColor Cyan
    Write-Host "  Listening on: 0.0.0.0:$x280Port" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Local access: $x280ApiBaseUrl/api/health" -ForegroundColor Cyan
    Write-Host "Remote access: http://100.127.121.20:$x280Port/api/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: If remote access fails, configure firewall:" -ForegroundColor Yellow
    Write-Host "  Run as Administrator:" -ForegroundColor Yellow
    Write-Host "  netsh advfirewall firewall add rule name=`"ManaOS X280 API Gateway`" dir=in action=allow protocol=TCP localport=$x280Port" -ForegroundColor Cyan
} catch {
    Write-Host "[WARNING] Could not verify API Gateway status" -ForegroundColor Yellow
    Write-Host "  Error: $_" -ForegroundColor Yellow
    Write-Host "  Process ID: $($process.Id)" -ForegroundColor Yellow
}

