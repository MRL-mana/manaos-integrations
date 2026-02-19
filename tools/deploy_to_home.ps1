<# 
  Deploy to ManaHome - Workshop to Production Bridge
  
  Purpose: Sync changes from manaos_integrations to D:\ManaHome safely
  
  Usage:
    PS> .\deploy_to_home.ps1 -DryRun              # Preview changes
    PS> .\deploy_to_home.ps1                      # Deploy with backups
    PS> .\deploy_to_home.ps1 -Rollback            # Restore from last backup
    PS> .\deploy_to_home.ps1 -SkipHealthCheck    # Deploy without probing
#>

param(
    [switch]$DryRun,
    [switch]$Rollback,
    [switch]$SkipHealthCheck,
    [string]$ConfigFile = ".\home_config.yaml"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorWarn = "Yellow"
$ColorInfo = "Cyan"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $output = "[$timestamp] [$Level] $Message"
    Write-Host $output
}

function Load-Config {
    if (-not (Test-Path $ConfigFile)) {
        Write-Log "Config file not found: $ConfigFile" "ERROR"
        exit 1
    }
    Write-Log "Loading config from: $ConfigFile"
    
    # Simple YAML parser for our config
    $config = @{}
    $content = Get-Content $ConfigFile -Raw
    
    # Basic YAML extraction
    $homePathMatch = $content | Select-String "home_path:\s+`"(.+?)`""
    if ($homePathMatch) {
        $config.home_path = $homePathMatch.Matches[0].Groups[1].Value
    }
    
    if (-not $config.home_path) {
        Write-Log "home_path not found in config" "ERROR"
        exit 1
    }
    
    return $config
}

function Test-HomeAvailable {
    param([string]$HomePath)
    
    if (-not (Test-Path $HomePath)) {
        Write-Log "Home path not found: $HomePath" "ERROR"
        return $false
    }
    
    $registryPath = Join-Path $HomePath "system\services\registry.yaml"
    if (-not (Test-Path $registryPath)) {
        Write-Log "Service registry not found at home: $registryPath" "ERROR"
        return $false
    }
    
    Write-Log "Home is available at: $HomePath" -Level INFO
    return $true
}

function Create-Backup {
    param([string]$HomePath)
    
    $backupDir = Join-Path $HomePath "system\backups\deploy"
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupName = "backup_$timestamp"
    $backupPath = Join-Path $backupDir $backupName
    
    # Backup only deployment targets
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    
    @("system\boot", "system\services", "skills", "adapters") | ForEach-Object {
        $source = Join-Path $HomePath $_
        if (Test-Path $source) {
            $dest = Join-Path $backupPath $_
            Copy-Item -Path $source -Destination $dest -Recurse -Force -ErrorAction Continue
        }
    }
    
    Write-Log "Backup created: $backupPath" -Level INFO
    return $backupPath
}

function Deploy-Files {
    param([string]$HomePath, [bool]$DryRun = $false)
    
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $deployed = 0
    $failed = 0
    
    Write-Log "Deployment mode: $(if($DryRun) {'DRY-RUN'} else {'LIVE'})"
    Write-Log "Source (workshop): $repoRoot"
    Write-Log "Destination (home): $HomePath"
    
    # Deployment targets
    $targets = @(
        @{source = "system/boot"; exclude = @("*.pid", "*.lock", "*.log") },
        @{source = "system/services"; exclude = @() },
        @{source = "skills"; exclude = @("__pycache__") },
        @{source = "adapters"; exclude = @("__pycache__") }
    )
    
    foreach ($target in $targets) {
        $srcPath = Join-Path $repoRoot $target.source
        if (-not (Test-Path $srcPath)) {
            Write-Log "Skipping $($target.source) - not found in workshop" -Level WARN
            continue
        }
        
        $destPath = Join-Path $HomePath $target.source
        
        Write-Log "Syncing: $($target.source)" -Level INFO
        
        if ($DryRun) {
            # Show what would be copied
            Get-ChildItem $srcPath -Recurse | Where-Object {
                $skip = $false
                foreach ($pattern in $target.exclude) {
                    if ($_.Name -like $pattern) {
                        $skip = $true
                        break
                    }
                }
                -not $skip
            } | ForEach-Object {
                $relPath = $_.FullName.Substring($srcPath.Length + 1)
                Write-Log "  [DRY] $relPath" -Level INFO
            }
        } else {
            # Actual copy
            Copy-Item -Path $srcPath -Destination $destPath -Recurse -Force -Exclude $target.exclude | Out-Null
            $deployed++
            Write-Log "  ✓ Synced" -Level INFO
        }
    }
    
    return @{
        deployed = $deployed
        failed = $failed
    }
}

function Test-HomeHealth {
    param([string]$HomePath)
    
    Write-Log "Running health check..." -Level INFO
    
    $ports = @(9502, 5106)
    $online = 0
    
    foreach ($port in $ports) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $result = $client.ConnectAsync('127.0.0.1', $port).Wait(900)
            $client.Close()
            
            if ($result) {
                Write-Log "  Port $port: ONLINE ✓" -Level INFO
                $online++
            } else {
                Write-Log "  Port $port: OFFLINE ✗" -Level WARN
            }
        } catch {
            Write-Log "  Port $port: ERROR" -Level ERROR
        }
        
        Start-Sleep -Milliseconds 100
    }
    
    Write-Log "Health result: $online/$($ports.Count) responding" -Level INFO
    return $online -ge ($ports.Count - 1)  # Allow 1 failure
}

function Rollback-Backup {
    param([string]$HomePath)
    
    $backupDir = Join-Path $HomePath "system\backups\deploy"
    if (-not (Test-Path $backupDir)) {
        Write-Log "No backups found" -Level ERROR
        return $false
    }
    
    # Get latest backup
    $latestBackup = Get-ChildItem $backupDir -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $latestBackup) {
        Write-Log "No valid backups found" -Level ERROR
        return $false
    }
    
    Write-Log "Rolling back from: $($latestBackup.Name)" -Level WARN
    
    @("system\boot", "system\services", "skills", "adapters") | ForEach-Object {
        $source = Join-Path $latestBackup.FullName $_
        if (Test-Path $source) {
            $dest = Join-Path $HomePath $_
            Copy-Item -Path $source -Destination $dest -Recurse -Force
            Write-Log "  Restored: $_" -Level INFO
        }
    }
    
    Write-Log "Rollback complete" -Level INFO
    return $true
}

# Main execution
function Main {
    Write-Host ""
    Write-Log "╔════════════════════════════════════════════════════╗" -Level INFO
    Write-Log "║  ManaHome Deploy - Workshop to Production Bridge  ║" -Level INFO
    Write-Log "╚════════════════════════════════════════════════════╝" -Level INFO
    Write-Host ""
    
    # Load config
    $config = Load-Config
    $homePath = $config.home_path
    
    # Rollback if requested
    if ($Rollback) {
        if (Rollback-Backup $homePath) {
            Write-Log "Rollback successful" -Level INFO
            exit 0
        } else {
            Write-Log "Rollback failed" -Level ERROR
            exit 1
        }
    }
    
    # Verify home is available
    if (-not (Test-HomeAvailable $homePath)) {
        exit 1
    }
    
    # Create backup
    if (-not $DryRun) {
        Create-Backup $homePath
    }
    
    # Deploy files
    $result = Deploy-Files $homePath $DryRun
    
    if ($DryRun) {
        Write-Log "DRY-RUN complete. No changes made." -Level INFO
        exit 0
    }
    
    # Health check
    if (-not $SkipHealthCheck) {
        Start-Sleep -Seconds 2
        if (Test-HomeHealth $homePath) {
            Write-Log "Health check PASSED ✓" -Level INFO
        } else {
            Write-Log "Health check FAILED - consider rollback" -Level WARN
        }
    }
    
    Write-Host ""
    Write-Log "═══════════════════════════════════════════════════" -Level INFO
    Write-Log "Deployment complete" -Level INFO
    Write-Log "Deployed: $($result.deployed) target(s)" -Level INFO
    Write-Log "═══════════════════════════════════════════════════" -Level INFO
    Write-Host ""
}

Main
