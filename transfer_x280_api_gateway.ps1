# Transfer x280_api_gateway.py to X280
# This script transfers the API Gateway Python script to X280

Write-Host "=== Transfer x280_api_gateway.py to X280 ===" -ForegroundColor Cyan
Write-Host ""

# Check if file exists
$sourceFile = "x280_api_gateway.py"
if (-not (Test-Path $sourceFile)) {
    Write-Host "[ERROR] $sourceFile not found in current directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Source file found: $sourceFile" -ForegroundColor Green
Write-Host ""

# X280 connection details
$x280Host = "x280"
$remoteDir = "C:\manaos_x280"
$remoteFile = "$remoteDir\x280_api_gateway.py"

Write-Host "[1/3] Creating remote directory if needed..." -ForegroundColor Yellow
ssh $x280Host "if (-not (Test-Path '$remoteDir')) { New-Item -ItemType Directory -Path '$remoteDir' -Force | Out-Null }"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Could not create remote directory (may already exist)" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Remote directory ready" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/3] Transferring file..." -ForegroundColor Yellow
scp $sourceFile "${x280Host}:${remoteFile}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] File transfer failed" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] File transferred successfully" -ForegroundColor Green
Write-Host ""

Write-Host "[3/3] Verifying transfer..." -ForegroundColor Yellow
$verifyResult = ssh $x280Host "Test-Path '$remoteFile'"
if ($verifyResult -match "True") {
    Write-Host "[OK] File verified on X280" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Could not verify file (may still be OK)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Transfer Complete ===" -ForegroundColor Cyan
Write-Host "File location on X280: $remoteFile" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. On X280, run: cd C:\manaos_x280" -ForegroundColor White
Write-Host "2. On X280, run: .\x280_api_gateway_start.ps1" -ForegroundColor White

