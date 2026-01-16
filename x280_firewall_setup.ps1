# X280 Firewall Setup for API Gateway
# This script opens port 5120 in Windows Firewall

$ErrorActionPreference = "Stop"

Write-Host "=== X280 Firewall Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] Administrator privileges required" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Running with administrator privileges" -ForegroundColor Green
Write-Host ""

# Check if rule already exists
Write-Host "[1/2] Checking firewall rules..." -ForegroundColor Yellow
$existingRule = Get-NetFirewallRule -DisplayName "ManaOS X280 API Gateway" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "[INFO] Firewall rule already exists" -ForegroundColor Gray
    Write-Host "Removing old rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "ManaOS X280 API Gateway" -ErrorAction SilentlyContinue
}

# Create firewall rule
Write-Host "[2/2] Creating firewall rule..." -ForegroundColor Yellow
try {
    New-NetFirewallRule `
        -DisplayName "ManaOS X280 API Gateway" `
        -Direction Inbound `
        -LocalPort 5120 `
        -Protocol TCP `
        -Action Allow `
        -Description "Allow inbound connections to X280 API Gateway on port 5120" | Out-Null
    
    Write-Host "[SUCCESS] Firewall rule created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Port 5120 is now open for inbound connections" -ForegroundColor Cyan
    Write-Host "Remote access: http://100.127.121.20:5120" -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Failed to create firewall rule: $_" -ForegroundColor Red
    exit 1
}

# Verify rule
Write-Host ""
Write-Host "Verifying firewall rule..." -ForegroundColor Yellow
$rule = Get-NetFirewallRule -DisplayName "ManaOS X280 API Gateway" -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "[OK] Firewall rule verified" -ForegroundColor Green
    Write-Host "  DisplayName: $($rule.DisplayName)" -ForegroundColor Gray
    Write-Host "  Enabled: $($rule.Enabled)" -ForegroundColor Gray
    Write-Host "  Direction: $($rule.Direction)" -ForegroundColor Gray
} else {
    Write-Host "[WARNING] Could not verify firewall rule" -ForegroundColor Yellow
}


















