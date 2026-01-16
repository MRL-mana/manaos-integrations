# X280 Firewall Setup - Administrator Required
# Run this script as Administrator on X280

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "=== X280 Firewall Setup (Administrator) ===" -ForegroundColor Cyan
Write-Host ""

# Check administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Navigate to: cd C:\manaos_x280" -ForegroundColor White
    Write-Host "4. Run: .\x280_firewall_admin.ps1" -ForegroundColor White
    exit 1
}

Write-Host "[OK] Running with administrator privileges" -ForegroundColor Green
Write-Host ""

# Remove existing rule if exists
Write-Host "[1/2] Checking existing firewall rules..." -ForegroundColor Yellow
$existingRule = netsh advfirewall firewall show rule name="ManaOS X280 API Gateway" 2>&1
if ($LASTEXITCODE -eq 0 -and -not ($existingRule -match "指定された規則が見つかりません")) {
    Write-Host "[INFO] Existing rule found. Removing..." -ForegroundColor Gray
    netsh advfirewall firewall delete rule name="ManaOS X280 API Gateway" 2>&1 | Out-Null
    Start-Sleep -Seconds 1
}

# Create firewall rule
Write-Host "[2/2] Creating firewall rule..." -ForegroundColor Yellow
try {
    $result = netsh advfirewall firewall add rule name="ManaOS X280 API Gateway" dir=in action=allow protocol=TCP localport=5120 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Firewall rule created!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Port 5120 is now open for inbound connections" -ForegroundColor Cyan
        Write-Host "Remote access: http://100.127.121.20:5120" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Verifying rule..." -ForegroundColor Yellow
        netsh advfirewall firewall show rule name="ManaOS X280 API Gateway" 2>&1 | Select-String -Pattern "有効|Enabled|ローカル ポート|LocalPort"
    } else {
        Write-Host "[ERROR] Failed to create firewall rule" -ForegroundColor Red
        Write-Host "Output: $result" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[ERROR] Exception occurred: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Firewall Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test remote access from another machine:" -ForegroundColor Yellow
Write-Host "  Invoke-RestMethod -Uri 'http://100.127.121.20:5120/api/health'" -ForegroundColor Cyan


















