# Require Administrator Privileges Helper Function
# Use this function in any PowerShell script that needs admin rights

function Require-Administrator {
    <#
    .SYNOPSIS
    Ensures the script is running with administrator privileges.
    
    .DESCRIPTION
    Checks if the current PowerShell session is running with administrator privileges.
    If not, it automatically restarts the script with administrator privileges.
    
    .EXAMPLE
    Require-Administrator
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
    
    Write-Host "[OK] Running with administrator privileges" -ForegroundColor Green
    Write-Host ""
}

# Export function for use in other scripts
Export-ModuleMember -Function Require-Administrator

