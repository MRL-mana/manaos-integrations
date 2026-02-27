param(
    [switch]$Json,
    [string]$JsonOutFile = "",
    [int]$TailLines = 20,
    [int]$MaxR12LogAgeMinutes = 30
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$r12Status = Join-Path $scriptDir "status_r12_health_watch_task.ps1"
$rlStatus = Join-Path $scriptDir "status_rl_anything_bootstrap_task.ps1"
$opsWatchStatus = Join-Path $scriptDir "status_r12_rl_ops_watch_task.ps1"
$r12Log = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"
$rlConfig = Join-Path $scriptDir "logs\rl_anything_bootstrap_task.config.json"
$opsWatchConfig = Join-Path $scriptDir "logs\r12_rl_ops_watch_task.config.json"

function Get-QueryValue {
    param(
        [string[]]$Names,
        [string[]]$Lines
    )

    foreach ($name in $Names) {
        $line = $Lines | Where-Object { $_ -match ("^" + [regex]::Escape($name) + "\s*:") } | Select-Object -First 1
        if ($null -ne $line) {
            return (($line -split ":", 2)[1]).Trim()
        }
    }

    return ""
}

function Get-TaskConfigStatus {
    param(
        [string]$TaskToRun,
        [string]$DefaultConfigFile
    )

    $issues = New-Object System.Collections.Generic.List[string]
    $configPath = ""
    $hasConfigArg = $false

    if (-not [string]::IsNullOrWhiteSpace($TaskToRun)) {
        $match = [regex]::Match($TaskToRun, '-ConfigFile\s+(?:"([^"]+)"|''([^'']+)''|(\S+))', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($match.Success) {
            $hasConfigArg = $true
            if (-not [string]::IsNullOrWhiteSpace($match.Groups[1].Value)) {
                $configPath = $match.Groups[1].Value
            }
            elseif (-not [string]::IsNullOrWhiteSpace($match.Groups[2].Value)) {
                $configPath = $match.Groups[2].Value
            }
            elseif (-not [string]::IsNullOrWhiteSpace($match.Groups[3].Value)) {
                $configPath = $match.Groups[3].Value
            }
        }
    }

    if (-not $hasConfigArg) {
        $issues.Add("Task command does not include -ConfigFile")
        $configPath = $DefaultConfigFile
    }

    if ([string]::IsNullOrWhiteSpace($configPath)) {
        $issues.Add("Config file path is empty")
        return @{
            hasConfigArg = $hasConfigArg
            configPath = $configPath
            configExists = $false
            configParseOk = $false
            issues = @($issues)
        }
    }

    $exists = Test-Path $configPath
    if (-not $exists) {
        $issues.Add("Config file not found: $configPath")
    }

    $parseOk = $false
    if ($exists) {
        try {
            $null = Get-Content -Path $configPath -Raw | ConvertFrom-Json
            $parseOk = $true
        }
        catch {
            $issues.Add("Config file parse failed: $configPath")
        }
    }

    return @{
        hasConfigArg = $hasConfigArg
        configPath = $configPath
        configExists = $exists
        configParseOk = $parseOk
        issues = @($issues)
    }
}

function Get-TaskSnapshot {
    param(
        [string]$TaskName,
        [switch]$RequireConfigFile,
        [string]$DefaultConfigFile = ""
    )

    $queryLines = schtasks /Query /TN $TaskName /V /FO LIST 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{
            taskName = $TaskName
            exists = $false
            isHealthy = $false
            issues = @("Task not found: $TaskName")
        }
    }

    $state = Get-QueryValue -Names @("状態", "Status") -Lines $queryLines
    $lastResult = Get-QueryValue -Names @("前回の結果", "Last Result") -Lines $queryLines
    $nextRun = Get-QueryValue -Names @("次回の実行時刻", "Next Run Time") -Lines $queryLines
    $lastRun = Get-QueryValue -Names @("前回の実行時刻", "Last Run Time") -Lines $queryLines
    $taskToRun = Get-QueryValue -Names @("実行するタスク", "Task To Run") -Lines $queryLines

    $issues = New-Object System.Collections.Generic.List[string]
    if ($state -and ($state -notin @("準備完了", "実行中", "Ready", "Running"))) {
        $issues.Add("Task state is not healthy: $state")
    }
    if ($lastResult -and ($lastResult -notin @("0", "0x0", "267009", "267011"))) {
        $issues.Add("Last result indicates failure: $lastResult")
    }

    $configStatus = $null
    if ($RequireConfigFile.IsPresent) {
        $configStatus = Get-TaskConfigStatus -TaskToRun $taskToRun -DefaultConfigFile $DefaultConfigFile
        foreach ($issue in @($configStatus.issues)) {
            $issues.Add($issue)
        }
    }

    return @{
        taskName = $TaskName
        exists = $true
        state = $state
        lastResult = $lastResult
        nextRun = $nextRun
        lastRun = $lastRun
        taskToRun = $taskToRun
        configStatus = $configStatus
        isHealthy = ($issues.Count -eq 0)
        issues = @($issues)
    }
}

function Get-R12LogSnapshot {
    param(
        [string]$LogPath,
        [int]$TailCount,
        [int]$MaxLogAgeMinutes
    )

    if (-not (Test-Path $LogPath)) {
        return @{
            exists = $false
            issues = @("Log file not found: $LogPath")
        }
    }

    $tail = Get-Content $LogPath -Tail $TailCount
    $latest = $null
    $lastLogAgeMinutes = $null
    $issues = New-Object System.Collections.Generic.List[string]
    $latestLine = Get-Content $LogPath -Tail 1
    if (-not [string]::IsNullOrWhiteSpace($latestLine)) {
        try {
            $latest = $latestLine | ConvertFrom-Json
            if ($null -ne $latest.failed -and [int]$latest.failed -gt 0) {
                $issues.Add("Latest log has failed endpoints: $($latest.failed)")
            }
            if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) {
                $latestTs = [datetimeoffset]::Parse([string]$latest.ts)
                $age = ([datetimeoffset]::Now - $latestTs).TotalMinutes
                $lastLogAgeMinutes = [math]::Round($age, 1)
                if ($age -gt $MaxLogAgeMinutes) {
                    $issues.Add(("Latest log is stale: {0:N1} min old" -f $age))
                }
            }
        } catch {
            $issues.Add("Failed to parse latest log line as JSON")
        }
    } else {
        $issues.Add("Log file is empty")
    }

    return @{
        exists = $true
        tail = @($tail)
        latest = $latest
        lastLogAgeMinutes = $lastLogAgeMinutes
        isHealthy = ($issues.Count -eq 0)
        issues = @($issues)
    }
}

function Write-ConfigLinkSummary {
    param(
        [string]$Label,
        $TaskSnapshot
    )

    if ($null -eq $TaskSnapshot -or -not $TaskSnapshot.exists) {
        Write-Host "[WARN] $Label config linkage: task missing" -ForegroundColor Yellow
        return
    }

    $cfg = $TaskSnapshot.configStatus
    if ($null -eq $cfg) {
        Write-Host "[WARN] $Label config linkage: not checked" -ForegroundColor Yellow
        return
    }

    $cfgIssues = @($cfg.issues)
    if ($cfgIssues.Count -eq 0) {
        Write-Host "[OK] $Label config linkage: OK | path=$($cfg.configPath)" -ForegroundColor Green
        return
    }

    $issueText = $cfgIssues -join '; '
    Write-Host "[WARN] $Label config linkage: WARN | path=$($cfg.configPath) | issues=$issueText" -ForegroundColor Yellow
}

if ($Json.IsPresent) {
    $r12Task = Get-TaskSnapshot -TaskName "ManaOS_R12_Health_Watch_5min"
    $rlTask = Get-TaskSnapshot -TaskName "ManaOS_RLAnything_Bootstrap_Logon" -RequireConfigFile -DefaultConfigFile $rlConfig
    $opsWatchTask = Get-TaskSnapshot -TaskName "ManaOS_R12_RL_Ops_Watch_15min" -RequireConfigFile -DefaultConfigFile $opsWatchConfig
    $r12LogSnapshot = Get-R12LogSnapshot -LogPath $r12Log -TailCount $TailLines -MaxLogAgeMinutes $MaxR12LogAgeMinutes

    $allIssues = @($r12Task.issues) + @($rlTask.issues) + @($opsWatchTask.issues) + @($r12LogSnapshot.issues)
    $payload = @{
        ok = ($allIssues.Count -eq 0)
        checkedAt = [datetimeoffset]::Now.ToString("o")
        r12Task = $r12Task
        rlTask = $rlTask
        opsWatchTask = $opsWatchTask
        r12Log = @{
            path = $r12Log
            exists = $r12LogSnapshot.exists
            latest = $r12LogSnapshot.latest
            tail = $r12LogSnapshot.tail
            lastLogAgeMinutes = $r12LogSnapshot.lastLogAgeMinutes
            isHealthy = $r12LogSnapshot.isHealthy
            issues = $r12LogSnapshot.issues
        }
        issues = $allIssues
    }

    $jsonText = ($payload | ConvertTo-Json -Depth 8)
    if (-not [string]::IsNullOrWhiteSpace($JsonOutFile)) {
        $jsonDir = Split-Path -Parent $JsonOutFile
        if (-not [string]::IsNullOrWhiteSpace($jsonDir) -and -not (Test-Path $jsonDir)) {
            New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
        }
        Set-Content -Path $JsonOutFile -Value $jsonText -Encoding UTF8
    }
    Write-Output $jsonText
    if ($payload.ok) { exit 0 }
    exit 1
}

Write-Host "=== Combined Ops Status (R12 + RL) ===" -ForegroundColor Cyan

pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Status
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlStatus
pwsh -NoProfile -ExecutionPolicy Bypass -File $opsWatchStatus

$rlTaskSnapshot = Get-TaskSnapshot -TaskName "ManaOS_RLAnything_Bootstrap_Logon" -RequireConfigFile -DefaultConfigFile $rlConfig
$opsWatchTaskSnapshot = Get-TaskSnapshot -TaskName "ManaOS_R12_RL_Ops_Watch_15min" -RequireConfigFile -DefaultConfigFile $opsWatchConfig

Write-Host ""
Write-Host "=== Config Linkage Summary ===" -ForegroundColor Cyan
Write-ConfigLinkSummary -Label "RLAnything" -TaskSnapshot $rlTaskSnapshot
Write-ConfigLinkSummary -Label "R12+RL Ops Watch" -TaskSnapshot $opsWatchTaskSnapshot

if (Test-Path $r12Log) {
    Write-Host "" 
    Write-Host "=== R12 Log Tail (last $TailLines) ===" -ForegroundColor Cyan
    Get-Content $r12Log -Tail $TailLines
} else {
    Write-Host "[INFO] r12 log not found: $r12Log" -ForegroundColor Yellow
}
