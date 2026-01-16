# Firewall Rule Addition Script (Admin Rights Required)
# Run this script as Administrator

$ErrorActionPreference = "Continue"

# Check for administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: This script requires administrator privileges" -ForegroundColor Red
    Write-Host "Please right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Adding Firewall Rule ===" -ForegroundColor Cyan
Write-Host ""

# Check for existing rule
$existingRule = Get-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "[INFO] Existing rule found" -ForegroundColor Yellow
    if ($existingRule.Enabled) {
        Write-Host "[OK] Rule is already enabled" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Enabling rule..." -ForegroundColor Yellow
        Enable-NetFirewallRule -DisplayName "Open WebUI Tailscale Access"
        Write-Host "[OK] Rule enabled" -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Adding new firewall rule..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" `
            -Direction Inbound `
            -LocalPort 3001 `
            -Protocol TCP `
            -Action Allow `
            -Profile Private,Public `
            -Description "Allow Tailscale access to Open WebUI on port 3001" `
            -ErrorAction Stop | Out-Null
        Write-Host "[OK] Firewall rule added successfully" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to add rule: $_" -ForegroundColor Red
        exit 1
    }
}

# Display rule details
Write-Host ""
Write-Host "=== Added Rule ===" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "Open WebUI Tailscale Access" | Format-List DisplayName, Enabled, Direction, Action, Profile

Write-Host ""
Write-Host "Complete!" -ForegroundColor Green
