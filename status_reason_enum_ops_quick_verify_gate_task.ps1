param(
    [string]$TaskName = "ManaOS_Reason_Enum_Ops_Quick_Verify_Gate_30min",
    [switch]$AsJson,
    [switch]$RequirePass
)

$ErrorActionPreference = "Stop"

function Get-SchtasksListValue {
    param(
        [string[]]$Lines,
        [string]$Pattern
    )

    $line = $Lines | Where-Object { $_ -match $Pattern } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($line)) {
        return ""
    }
    $parts = $line -split ':', 2
    if ($parts.Count -lt 2) {
        return ""
    }
    return [string]$parts[1].Trim()
}

function Test-TaskLastResultOk {
    param([string]$LastResult)

    if ([string]::IsNullOrWhiteSpace($LastResult)) {
        return $false
    }

    $candidate = $LastResult.Trim()
    if ($candidate -match '^(0|0x0)$') {
        return $true
    }
    if ($candidate -match '^(The operation completed successfully\.|操作は正しく終了しました\.)$') {
        return $true
    }

    return $false
}

$payload = [ordered]@{
    task_name = $TaskName
    task_found = $false
    task_to_run = ""
    task_status = ""
    task_running = $false
    task_last_run_time = ""
    task_next_run_time = ""
    task_last_result = ""
    task_last_result_ok = $false
    ok_reason = "task_not_found"
}

$taskInfo = schtasks /Query /TN $TaskName /V /FO LIST 2>$null
if ($LASTEXITCODE -ne 0 -or $null -eq $taskInfo) {
    if ($AsJson) {
        $payload.require_pass = [bool]$RequirePass
        $payload.pass = $false
        Write-Output ($payload | ConvertTo-Json -Depth 8)
    }
    else {
        Write-Host "=== Reason Enum Ops Quick Verify Gate Task Status ===" -ForegroundColor Cyan
        Write-Host "TaskName: $TaskName" -ForegroundColor Gray
        Write-Host "[INFO] Task not found: $TaskName" -ForegroundColor Yellow
        Write-Host "ok_reason: task_not_found" -ForegroundColor Gray
    }
    exit 1
}

$payload.task_found = $true
$payload.task_to_run = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Task To Run|実行するタスク):\s*'
$payload.task_status = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Status|状態):\s*'
$payload.task_running = [bool]($payload.task_status -match '^(Running|実行中)$')
$payload.task_last_run_time = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Last Run Time|前回の実行時刻):\s*'
$payload.task_next_run_time = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Next Run Time|次回の実行時刻):\s*'
$payload.task_last_result = Get-SchtasksListValue -Lines $taskInfo -Pattern '^(Last Result|前回の結果):\s*'
$payload.task_last_result_ok = Test-TaskLastResultOk -LastResult $payload.task_last_result
$payload.ok_reason = if ($payload.task_last_result_ok) { 'ok' } elseif ($payload.task_running) { 'running' } else { 'last_result_not_success' }

$pass = ($payload.task_found -and ($payload.task_last_result_ok -or $payload.task_running))

if ($AsJson) {
    $payload.require_pass = [bool]$RequirePass
    $payload.pass = $pass
    Write-Output ($payload | ConvertTo-Json -Depth 8)
    if ($RequirePass.IsPresent -and -not $pass) {
        exit 1
    }
    exit 0
}

Write-Host "=== Reason Enum Ops Quick Verify Gate Task Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName" -ForegroundColor Gray
$taskInfo | ForEach-Object { Write-Host $_ }
if (-not [string]::IsNullOrWhiteSpace($payload.task_to_run)) {
    Write-Host "---" -ForegroundColor DarkGray
    Write-Host "TaskToRun: $($payload.task_to_run)" -ForegroundColor Gray
}
Write-Host "task_last_result_ok: $($payload.task_last_result_ok)" -ForegroundColor Gray
Write-Host "task_running: $($payload.task_running)" -ForegroundColor Gray
Write-Host "ok_reason: $($payload.ok_reason)" -ForegroundColor Gray
Write-Host "pass: $pass" -ForegroundColor Gray

if ($RequirePass.IsPresent -and -not $pass) {
    Write-Host "[ALERT] quick verify gate task status is not pass" -ForegroundColor Red
    exit 1
}

exit 0
