# Deploy X280 Auto-start Setup Script to X280
# This script transfers the auto-start setup script to X280

Write-Host "=== Deploy X280 Auto-start Setup Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if file exists
$sourceFile = "x280_setup_autostart.ps1"
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
$remoteFile = "$remoteDir\x280_setup_autostart.ps1"

Write-Host "[1/2] Transferring file..." -ForegroundColor Yellow
scp $sourceFile "${x280Host}:${remoteFile}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] File transfer failed" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] File transferred successfully" -ForegroundColor Green
Write-Host ""

Write-Host "[2/2] Instructions for X280:" -ForegroundColor Yellow
Write-Host ""
Write-Host "On X280, run:" -ForegroundColor White
Write-Host "  cd C:\manaos_x280" -ForegroundColor Cyan
Write-Host "  .\x280_setup_autostart.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: This script requires administrator privileges" -ForegroundColor Yellow
Write-Host "      It will automatically request elevation if needed" -ForegroundColor Yellow

