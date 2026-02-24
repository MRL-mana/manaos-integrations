# Daily Health Check Script
# ファイル: C:\Users\mana4\Desktop\manaos_integrations\tools\daily_health_check.ps1
# 目的: 毎日の運用安定性を確認し、ログに記録する
# 実行: Windows Task Scheduler で毎日 08:00 と 20:00 に実行

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
$RequiredLogFiles = @(
    "$TargetHome\system\runtime\logs\home_boot_v2.log",
    "$TargetHome\system\runtime\logs\home_update_v2.log"
)
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
    $process = Get-Process | Where-Object { $_.ProcessName -like $ProcessNamePattern -or $_.CommandLine -like \"*$ProcessNamePattern*\" } | Select-Object -First 1
    if ($process) {
        return [math]::Round($process.WorkingSet / 1MB)
    }
    return 0
}

function Write-CheckResult {
    param(
        [string]$CheckName,
        [bool]$Passed,
        [string]$Details = \"\"
    )
    
    $status = if ($Passed) { \"✓ PASS\" } else { \"✗ FAIL\" }
    $logMessage = \"[$timestamp] $CheckName: $status $(if ($Details) { \"| $Details\" } else { \"\" })\"
    Add-Content -Path $healthCheckLog -Value $logMessage
    Write-Host $logMessage
    
    return @{ Name = $CheckName; Passed = $Passed; Details = $Details }
}

# ================================
# Main Script
# ================================

# ファイルパス設定
$timestamp = Get-Date -Format \"yyyy-MM-dd HH:mm:ss\"
$dateOnly = Get-Date -Format \"yyyy-MM-dd\"
$healthCheckLog = \"$TargetHome\\system\\runtime\\logs\\health_check_$dateOnly.log\"

# ログヘッダー
if (-not (Test-Path $healthCheckLog)) {
    New-Item -ItemType File -Path $healthCheckLog -Force | Out-Null
    Add-Content -Path $healthCheckLog -Value \"# Daily Health Check Log - $dateOnly\"
    Add-Content -Path $healthCheckLog -Value \"\"
}

Write-Host \"=========================\"
Write-Host \"Daily Health Check\"
Write-Host \"Time: $timestamp\"
Write-Host \"=========================\"
Add-Content -Path $healthCheckLog -Value \"`n=== Check Run: $timestamp ===\"

$results = @()

# Check 1: Home directory availability
$homeAvailable = Test-Path $TargetHome
$results += Write-CheckResult \"Home Directory\" $homeAvailable \"$TargetHome\"

# Check 2: Core Services (16/16)
Write-Host \"`nCheck 2: Core Services...\"
$onlineCount = 0
$failedPorts = @()

foreach ($port in $CorePorts) {
    if (Test-Port $port) {
        $onlineCount++
    } else {
        $failedPorts += $port
    }
}

$coreStatus = $onlineCount -eq $CorePorts.Count
$details = \"$onlineCount/$($CorePorts.Count)\"
if ($failedPorts.Count -gt 0) {
    $details += \" Failed ports: $($failedPorts -join ',')\"
}
$results += Write-CheckResult \"Core Services\" $coreStatus $details

# Check 3: Optional Services
Write-Host \"`nCheck 3: Optional Services...\"
$opt8088 = Test-Port 8088
$opt8188 = Test-Port 8188
$optionalStatus = $opt8088 -and $opt8188
$details = \"8088=$opt8088, 8188=$opt8188\"
$results += Write-CheckResult \"Optional Services\" $optionalStatus $details

# Check 4: Required Log Files Exist
Write-Host \"`nCheck 4: Log Files...\"
$logsExist = 0
foreach ($logFile in $RequiredLogFiles) {
    if (Test-Path $logFile) { $logsExist++ }
}
$logsStatus = $logsExist -eq $RequiredLogFiles.Count
$results += Write-CheckResult \"Log Files\" $logsStatus \"$logsExist/$($RequiredLogFiles.Count) present\"

# Check 5: state.json Currency
Write-Host \"`nCheck 5: State File...\"
if (Test-Path $StateFile) {
    $stateAge = (Get-Date) - (Get-Item $StateFile).LastWriteTime
    $stateStatus = $stateAge.TotalSeconds -lt 300  # 5分以内に更新された
    $results += Write-CheckResult \"State File\" $stateStatus \"Age: $([math]::Round($stateAge.TotalSeconds))s\"
} else {
    $results += Write-CheckResult \"State File\" $false \"File not found\"
}

# Check 6: Disk Space
Write-Host \"`nCheck 6: Disk Space...\"
$drive = Get-PSDrive D
$freeGB = [math]::Round($drive.Free / 1GB)
$diskStatus = $freeGB -gt 10
$results += Write-CheckResult \"Disk Space\" $diskStatus \"${freeGB}GB free\"

# Check 7: Recent Errors in Logs
Write-Host \"`nCheck 7: Log Errors...\"
$recentErrors = 0
foreach ($logFile in $RequiredLogFiles) {
    if (Test-Path $logFile) {
        $errors = Get-Content $logFile | Select-String \"ERROR|FAILED|Exception\" | Select-Object -Last 5
        if ($errors) { $recentErrors += $errors.Count }
    }
}
$errorStatus = $recentErrors -le 5
$results += Write-CheckResult \"Log Errors\" $errorStatus \"Recent errors: $recentErrors\"

# Check 8: Process Memory Usage
Write-Host \"`nCheck 8: Memory Usage...\"
$pythonMemory = Get-ProcessMemoryMB \"python\"
$memoryStatus = $pythonMemory -lt 500  # 500MB以内が目安
$results += Write-CheckResult \"Python Processes\" $memoryStatus \"${pythonMemory}MB\"

# Check 9: Windows Startup Registration
Write-Host \"`nCheck 9: Windows Startup...\"
$startupFolder = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs\\Startup'
$autoStartFile = Join-Path $startupFolder 'ManaOS_AutoStart.cmd'
$startupStatus = Test-Path $autoStartFile
$results += Write-CheckResult \"Startup Registration\" $startupStatus \"$autoStartFile\"

# ================================
# Summary Report
# ================================
$passCount = ($results | Where-Object { $_.Passed }).Count
$totalCount = $results.Count

$summary = @\"

=== SUMMARY ===
Passed: $passCount / $totalCount
Timestamp: $timestamp
Status: $(if ($passCount -eq $totalCount) { \"✓ HEALTHY\" } elseif ($passCount -gt ($totalCount * 0.9)) { \"⚠ WARNING\" } else { \"✗ CRITICAL\" })

\"@

Write-Host $summary
Add-Content -Path $healthCheckLog -Value $summary

# Alert if needed
if ($SendAlert -and $passCount -lt ($totalCount * 0.95)) {
    Write-Host \"⚠️ Sending alert email...\"
    
    if ($AlertEmail) {
        $failedChecks = $results | Where-Object { -not $_.Passed } | ForEach-Object { $_.Name }
        $mailBody = @\"
ManaOS Health Check Alert
Timestamp: $timestamp
Failed Checks: $($failedChecks -join ', ')

Please review the health_check log at: $healthCheckLog
\"@
        # Send-MailMessage -To $AlertEmail -From \"manaos@internal\" -Subject \"ManaOS Health Alert\" -Body $mailBody
        # NOTE: 実装に email サーバー設定が必要
    }
}

Write-Host \"`n✓ Health check completed. Log saved to: $healthCheckLog\"
