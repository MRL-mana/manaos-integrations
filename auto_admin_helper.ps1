# Auto-Admin Helper Function
# Include this at the beginning of any script that needs admin privileges

function Request-AdminPrivileges {
    <#
    .SYNOPSIS
    Automatically requests administrator privileges if not already running as admin.
    
    .DESCRIPTION
    Checks if the current PowerShell session is running with administrator privileges.
    If not, it automatically restarts the script with administrator privileges using UAC.
    
    .EXAMPLE
    Request-AdminPrivileges
    #>
    
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "[INFO] Administrator privileges required" -ForegroundColor Yellow
        Write-Host "Restarting script with administrator privileges..." -ForegroundColor Cyan
        Write-Host ""
        
        # Get the script path
        $scriptPath = $MyInvocation.ScriptName
        if (-not $scriptPath) {
            $scriptPath = $MyInvocation.MyCommand.Path
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
            Write-Host "[ERROR] Failed to restart with administrator privileges: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please run PowerShell as Administrator manually:" -ForegroundColor Yellow
            Write-Host "1. Right-click PowerShell" -ForegroundColor White
            Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
            Write-Host "3. Run this script again" -ForegroundColor White
            exit 1
        }
    }
    
    return $true
}

# Auto-execute if called directly
if ($MyInvocation.InvocationName -ne '.') {
    Request-AdminPrivileges
}

