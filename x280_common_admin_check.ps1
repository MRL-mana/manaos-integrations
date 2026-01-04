# X280 Common Admin Check Function
# Same as common_admin_check.ps1 but for X280 (Windows PC)
# Add this at the beginning of any script that might need admin privileges

# Check administrator privileges and restart as admin if needed
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] Administrator privileges may be required" -ForegroundColor Yellow
    Write-Host "Restarting script with administrator privileges..." -ForegroundColor Cyan
    Write-Host ""
    
    # Get the script path
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.ScriptName
    }
    
    # Get all arguments
    $arguments = "-ExecutionPolicy Bypass -File `"$scriptPath`""
    
    # Add original arguments if any
    if ($args.Count -gt 0) {
        $arguments += " " + ($args -join " ")
    }
    
    # Start new PowerShell process as administrator
    try {
        Start-Process powershell -Verb RunAs -ArgumentList $arguments
        exit 0
    } catch {
        Write-Host "[WARNING] Failed to restart with administrator privileges: $_" -ForegroundColor Yellow
        Write-Host "Continuing without administrator privileges..." -ForegroundColor Yellow
        Write-Host ""
    }
}

