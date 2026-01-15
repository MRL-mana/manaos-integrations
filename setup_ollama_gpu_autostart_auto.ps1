# Ollama GPU Mode Auto-start Setup (Auto-admin)
# Automatically requests administrator privileges and sets up auto-start

$scriptPath = Join-Path $PSScriptRoot "setup_ollama_gpu_autostart.ps1"

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -NoExit -File `"$scriptPath`""
    exit
}

# If already admin, run the setup script
& $scriptPath
