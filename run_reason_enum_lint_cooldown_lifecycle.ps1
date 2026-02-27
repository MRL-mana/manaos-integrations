param(
    [string]$TaskName = "ManaOS_Reason_Enum_Lint_Cooldown_Verify_Weekly",
    [string]$Day = "SUN",
    [string]$StartTime = "03:30",
    [int]$NotifyFailureCooldownMinutes = 60,
    [int]$WaitAfterRunSeconds = 6,
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = "",
    [switch]$RequirePassAfterRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\reason_enum_cooldown_lifecycle.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\reason_enum_cooldown_lifecycle.history.jsonl"
}

$installScript = Join-Path $scriptDir "install_reason_enum_lint_cooldown_verify_task.ps1"
$statusScript = Join-Path $scriptDir "status_reason_enum_lint_cooldown_verify_task.ps1"
$lifecycleStatusScript = Join-Path $scriptDir "status_reason_enum_lint_cooldown_lifecycle.ps1"
$verifyScript = Join-Path $scriptDir "verify_reason_enum_lint_cooldown.ps1"
$uninstallScript = Join-Path $scriptDir "uninstall_reason_enum_lint_cooldown_verify_task.ps1"

foreach ($required in @($installScript, $statusScript, $lifecycleStatusScript, $verifyScript, $uninstallScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$Args
    )

    $cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $Args
    $output = @(& pwsh @cmdArgs 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        name = $Name
        script = $ScriptPath
        args = $Args
        exit_code = [int]$exitCode
        ok = ([int]$exitCode -eq 0)
        output_tail = @($output | Select-Object -Last 20)
    }
}

$latestDir = Split-Path -Parent $LatestJsonFile
if ($latestDir -and -not (Test-Path $latestDir)) {
    New-Item -ItemType Directory -Path $latestDir -Force | Out-Null
}
$historyDir = Split-Path -Parent $HistoryJsonl
if ($historyDir -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
}

$runTs = [datetimeoffset]::Now.ToString('o')
$steps = New-Object System.Collections.Generic.List[object]

$steps.Add((Invoke-Step -Name 'uninstall' -ScriptPath $uninstallScript -Args @('-TaskName', $TaskName)))
$steps.Add((Invoke-Step -Name 'install' -ScriptPath $installScript -Args @('-TaskName', $TaskName, '-Day', $Day, '-StartTime', $StartTime, '-NotifyFailureCooldownMinutes', "$NotifyFailureCooldownMinutes", '-WaitAfterRunSeconds', "$WaitAfterRunSeconds")))
$steps.Add((Invoke-Step -Name 'status_before_verify' -ScriptPath $statusScript -Args @('-TaskName', $TaskName)))
$steps.Add((Invoke-Step -Name 'verify_run_once' -ScriptPath $verifyScript -Args @('-TaskName', $TaskName, '-NotifyFailureCooldownMinutes', "$NotifyFailureCooldownMinutes", '-WaitAfterRunSeconds', "$WaitAfterRunSeconds")))
$steps.Add((Invoke-Step -Name 'status_after_verify' -ScriptPath $statusScript -Args @('-TaskName', $TaskName)))

$failed = @($steps | Where-Object { -not $_.ok })
$ok = ($failed.Count -eq 0)
$okReason = if ($ok) { 'cooldown_lifecycle_passed' } else { 'cooldown_lifecycle_failed' }
$failedStepNames = @($failed | ForEach-Object { [string]$_.name })
$allSteps = $steps.ToArray()
$postCheckAttempted = $false
$postCheckExit = -1
$postCheckOk = $false
$postCheckOutputTail = @()

$statusAfter = $steps | Where-Object { $_.name -eq 'status_after_verify' } | Select-Object -First 1
$statusSummary = @()
if ($null -ne $statusAfter) {
    $statusSummary = @($statusAfter.output_tail | Where-Object {
        $_ -match 'latest_ok:' -or $_ -match 'latest_ok_reason:' -or $_ -match 'latest_failure_notify_suppressed_reason:' -or $_ -match 'state_last_status:' -or $_ -match 'task_last_result_meaning:'
    })
}

if ($RequirePassAfterRun.IsPresent) {
    $postCheckAttempted = $true
    $postCheckArgs = @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$lifecycleStatusScript,
        '-LatestJsonFile',$LatestJsonFile,
        '-HistoryJsonl',$HistoryJsonl,
        '-RequirePass',
        '-AsJson'
    )
    $postCheckOutput = @(& pwsh @postCheckArgs 2>&1 | ForEach-Object { [string]$_ })
    $postCheckExit = $LASTEXITCODE
    $postCheckOk = ($postCheckExit -eq 0)
    $postCheckOutputTail = @($postCheckOutput | Select-Object -Last 20)

    if (-not $postCheckOk) {
        $ok = $false
        if ($okReason -eq 'cooldown_lifecycle_passed') {
            $okReason = 'cooldown_lifecycle_postcheck_failed'
        }
        $failedStepNames += 'lifecycle_require_pass'
    }
}

$payload = [ordered]@{
    ts = $runTs
    ok = $ok
    ok_reason = $okReason
    task_name = $TaskName
    day = $Day
    start_time = $StartTime
    notify_failure_cooldown_minutes = [int]$NotifyFailureCooldownMinutes
    wait_after_run_seconds = [int]$WaitAfterRunSeconds
    require_pass_after_run = [bool]$RequirePassAfterRun
    post_check_attempted = $postCheckAttempted
    post_check_ok = $postCheckOk
    post_check_exit_code = [int]$postCheckExit
    post_check_output_tail = $postCheckOutputTail
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    failed_step_count = $failedStepNames.Count
    failed_steps = $failedStepNames
    status_after_summary = $statusSummary
    steps = $allSteps
}

($payload | ConvertTo-Json -Depth 10) | Set-Content -Path $LatestJsonFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8

Write-Host "=== Reason Enum Cooldown Lifecycle ===" -ForegroundColor Cyan
Write-Host "ok: $ok" -ForegroundColor Gray
Write-Host "ok_reason: $okReason" -ForegroundColor Gray
Write-Host "failed_step_count: $($failed.Count)" -ForegroundColor Gray
if ($statusSummary.Count -gt 0) {
    Write-Host "--- status_after_summary ---" -ForegroundColor Cyan
    $statusSummary | ForEach-Object { Write-Host $_ }
}

if ($ok) {
    Write-Host "[OK] cooldown lifecycle completed" -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] cooldown lifecycle failed" -ForegroundColor Red
$failed | ForEach-Object {
    Write-Host ("[FAILED] {0} exit={1}" -f $_.name, $_.exit_code) -ForegroundColor Red
}
exit 1
