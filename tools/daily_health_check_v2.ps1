# Daily Health Check Script
# Purpose: Daily operational stability check and logging
# Usage: Windows Task Scheduler at 08:00 and 20:00 daily

param(
    [string]$TargetHome = "D:\ManaHome",
    [bool]$SendAlert = $true,
    [string]$AlertEmail = $null
)

# ================================
# Configuration
# ================================
$CorePorts = @(9502,5106,5105,5104,5126,5117,5120,5121,5122,5123,5124,5125,5127,5128,5129,5130)
$OptionalPorts = @(8088,8188)
$StateFile = "$TargetHome\system\runtime\state.json"

# ================================
# Helper Functions
# ================================
function Test-Port {
    param([int]$Port, [int]$TimeoutMs = 900)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.ConnectAsync('127.0.0.1', $Port)
        if ($async.Wait($TimeoutMs)) {
            $client.Close()
            return $true
        } else {
            return $false
        }
    } catch {
        return $false
    }
}

function Get-ProcessMemoryMB {
    param([string]$ProcessNamePattern)
    $process = Get-Process | Where-Object { $_.ProcessName -like $ProcessNamePattern } | Select-Object -First 1
    if ($process) {
        return [math]::Round($process.WorkingSet / 1MB)
    }
    return 0
}

# ================================
# Main Script
# ================================

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$dateOnly = Get-Date -Format "yyyy-MM-dd"
$healthCheckLog = "$TargetHome\system\runtime\logs\health_check_$dateOnly.log"

# Create log if doesn't exist
if (-not (Test-Path $healthCheckLog)) {
    New-Item -ItemType File -Path $healthCheckLog -Force | Out-Null
    Add-Content -Path $healthCheckLog -Value "# Daily Health Check Log - $dateOnly"
}

Write-Host "========================="
Write-Host "Daily Health Check"
Write-Host "Time: $timestamp"
Write-Host "========================="
Add-Content -Path $healthCheckLog -Value "`n=== Check Run: $timestamp ==="

$results = @()
$passCount = 0
$totalCount = 0

# Check 1: Home directory availability
Write-Host "`nCheck 1: Home Directory..."
$homeAvailable = Test-Path $TargetHome
$status = if ($homeAvailable) { "✓ PASS" } else { "✗ FAIL" }
Write-Host "  $status - $TargetHome"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Home Directory: $status"
if ($homeAvailable) { $passCount++ }
$totalCount++

# Check 2: Core Services (16/16)
Write-Host "`nCheck 2: Core Services..."
$onlineCount = 0
$failedPorts = @()

foreach ($port in $CorePorts) {
    if (Test-Port $port) {
        $onlineCount++
    } else {
        $failedPorts += $port
    }
}

$coreStatus = if ($onlineCount -eq $CorePorts.Count) { "✓ PASS" } else { "✗ FAIL" }
$details = "$onlineCount/$($CorePorts.Count)"
if ($failedPorts.Count -gt 0) {
    $details += " Failed: $($failedPorts -join ',')"
}
Write-Host "  $coreStatus - Core services online: $details"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Core Services: $coreStatus | $details"
if ($onlineCount -eq $CorePorts.Count) { $passCount++ }
$totalCount++

# Check 3: Optional Services
Write-Host "`nCheck 3: Optional Services..."
$opt8088 = Test-Port 8088
$opt8188 = Test-Port 8188
$optionalStatus = if ($opt8088 -and $opt8188) { "✓ PASS" } else { "✗ FAIL" }
$details = "8088=$opt8088, 8188=$opt8188"
Write-Host "  $optionalStatus - $details"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Optional Services: $optionalStatus | $details"
if ($opt8088 -and $opt8188) { $passCount++ }
$totalCount++

# Check 4: Required Log Files
Write-Host "`nCheck 4: Log Files..."
$bootLogExists = Test-Path "$TargetHome\system\runtime\logs\home_boot_v2.log"
$updateLogExists = Test-Path "$TargetHome\system\runtime\logs\home_update_v2.log"
$logsStatus = if ($bootLogExists -and $updateLogExists) { "✓ PASS" } else { "✗ FAIL" }
$details = "boot=$bootLogExists, update=$updateLogExists"
Write-Host "  $logsStatus - $details"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Log Files: $logsStatus | $details"
if ($bootLogExists -and $updateLogExists) { $passCount++ }
$totalCount++

# Check 5: state.json Currency
Write-Host "`nCheck 5: State File..."
if (Test-Path $StateFile) {
    $stateAge = (Get-Date) - (Get-Item $StateFile).LastWriteTime
    $stateStatus = if ($stateAge.TotalSeconds -lt 300) { "✓ PASS" } else { "✗ FAIL" }
    $details = "Age: $([math]::Round($stateAge.TotalSeconds))s"
    Write-Host "  $stateStatus - $details"
    Add-Content -Path $healthCheckLog -Value "[$timestamp] State File: $stateStatus | $details"
    if ($stateAge.TotalSeconds -lt 300) { $passCount++ }
} else {
    Write-Host "  ✗ FAIL - File not found"
    Add-Content -Path $healthCheckLog -Value "[$timestamp] State File: ✗ FAIL | File not found"
}
$totalCount++

# Check 6: Disk Space
Write-Host "`nCheck 6: Disk Space..."
$drive = Get-PSDrive D
$freeGB = [math]::Round($drive.Free / 1GB)
$diskStatus = if ($freeGB -gt 10) { "✓ PASS" } else { "✗ FAIL" }
Write-Host "  $diskStatus - ${freeGB}GB free"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Disk Space: $diskStatus | ${freeGB}GB"
if ($freeGB -gt 10) { $passCount++ }
$totalCount++

# Check 7: Recent Errors
Write-Host "`nCheck 7: Log Errors..."
$recentErrors = 0
$bootLog = "$TargetHome\system\runtime\logs\home_boot_v2.log"
$updateLog = "$TargetHome\system\runtime\logs\home_update_v2.log"

if (Test-Path $bootLog) {
    $errors = Get-Content $bootLog | Select-String "ERROR|FAILED|Exception" | Measure-Object
    $recentErrors += $errors.Count
}
if (Test-Path $updateLog) {
    $errors = Get-Content $updateLog | Select-String "ERROR|FAILED|Exception" | Measure-Object
    $recentErrors += $errors.Count
}

$errorStatus = if ($recentErrors -le 5) { "✓ PASS" } else { "✗ FAIL" }
Write-Host "  $errorStatus - Recent errors: $recentErrors"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Log Errors: $errorStatus | Count: $recentErrors"
if ($recentErrors -le 5) { $passCount++ }
$totalCount++

# Check 8: Process Memory
Write-Host "`nCheck 8: Memory Usage..."
$pythonMemory = Get-ProcessMemoryMB "python"
$memoryStatus = if ($pythonMemory -lt 500) { "✓ PASS" } else { "✗ FAIL" }
Write-Host "  $memoryStatus - ${pythonMemory}MB"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Memory Usage: $memoryStatus | ${pythonMemory}MB"
if ($pythonMemory -lt 500) { $passCount++ }
$totalCount++

# Check 9: Windows Startup
Write-Host "`nCheck 9: Windows Startup..."
$startupFolder = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$autoStartFile = Join-Path $startupFolder 'ManaOS_AutoStart.cmd'
$startupStatus = if (Test-Path $autoStartFile) { "✓ PASS" } else { "✗ FAIL" }
Write-Host "  $startupStatus - Startup registration"
Add-Content -Path $healthCheckLog -Value "[$timestamp] Startup: $startupStatus"
if (Test-Path $autoStartFile) { $passCount++ }
$totalCount++

# ================================
# Summary Report
# ================================
Write-Host "`n========================="
Write-Host "SUMMARY"
Write-Host "Passed: $passCount / $totalCount"
Write-Host "Timestamp: $timestamp"
$summaryStatus = if ($passCount -eq $totalCount) { "✓ HEALTHY" } elseif ($passCount -gt ($totalCount * 0.9)) { "⚠ WARNING" } else { "✗ CRITICAL" }
Write-Host "Status: $summaryStatus"
Write-Host "========================="

$summary = @"

=== SUMMARY ===
Passed: $passCount / $totalCount
Timestamp: $timestamp
Status: $summaryStatus
Log location: $healthCheckLog
"@

Add-Content -Path $healthCheckLog -Value $summary

Write-Host "`n✓ Health check completed. Log: $healthCheckLog"
