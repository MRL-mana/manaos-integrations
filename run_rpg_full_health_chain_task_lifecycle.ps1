param(
    [string]$TaskName = "ManaOS_RPG_Full_Health_Chain_30min",
    [int]$IntervalMinutes = 30,
    [string]$LatestJsonFile = "",
    [string]$HistoryJsonl = "",
    [int]$MaxHistoryLines = 1000,
    [switch]$KeepInstalled
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($LatestJsonFile)) {
    $LatestJsonFile = Join-Path $scriptDir "logs\rpg_full_health_chain_task_lifecycle.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\rpg_full_health_chain_task_lifecycle.history.jsonl"
}
if ($MaxHistoryLines -lt 1) {
    throw "MaxHistoryLines must be >= 1"
}

$installScript = Join-Path $scriptDir "install_rpg_full_health_chain_task.ps1"
$uninstallScript = Join-Path $scriptDir "uninstall_rpg_full_health_chain_task.ps1"
$statusScript = Join-Path $scriptDir "status_rpg_full_health_chain_task.ps1"
$runOnceScript = Join-Path $scriptDir "run_rpg_full_health_chain_once.ps1"

foreach ($required in @($installScript, $uninstallScript, $statusScript, $runOnceScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [string[]]$StepValues,
        [int[]]$ExpectedExitCodes = @(0)
    )

    $commandValues = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $StepValues
    $output = @(& pwsh @commandValues 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = [int]$LASTEXITCODE
    $ok = ($ExpectedExitCodes -contains $exitCode)

    return [pscustomobject]@{
        name = $Name
        script = $ScriptPath
        values = $StepValues
        expected_exit_codes = $ExpectedExitCodes
        exit_code = $exitCode
        ok = $ok
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

$steps.Add((Invoke-Step -Name 'uninstall_pre' -ScriptPath $uninstallScript -StepValues @('-TaskName', $TaskName)))
$steps.Add((Invoke-Step -Name 'status_expect_missing' -ScriptPath $statusScript -StepValues @('-TaskName', $TaskName, '-AsJson') -ExpectedExitCodes @(1)))
$steps.Add((Invoke-Step -Name 'run_once' -ScriptPath $runOnceScript -StepValues @()))
$steps.Add((Invoke-Step -Name 'install' -ScriptPath $installScript -StepValues @('-TaskName', $TaskName, '-IntervalMinutes', "$IntervalMinutes")))
$steps.Add((Invoke-Step -Name 'status_after_install_json' -ScriptPath $statusScript -StepValues @('-TaskName', $TaskName, '-AsJson')))
$steps.Add((Invoke-Step -Name 'status_after_install_require_pass' -ScriptPath $statusScript -StepValues @('-TaskName', $TaskName, '-RequirePass')))

if (-not $KeepInstalled.IsPresent) {
    $steps.Add((Invoke-Step -Name 'uninstall_post' -ScriptPath $uninstallScript -StepValues @('-TaskName', $TaskName)))
    $steps.Add((Invoke-Step -Name 'status_after_uninstall_expect_missing' -ScriptPath $statusScript -StepValues @('-TaskName', $TaskName, '-AsJson') -ExpectedExitCodes @(1)))
}

$failed = @($steps | Where-Object { -not $_.ok })
$ok = ($failed.Count -eq 0)
$okReason = if ($ok) { 'rpg_full_health_chain_task_lifecycle_passed' } else { 'rpg_full_health_chain_task_lifecycle_failed' }
$failedStepNames = @($failed | ForEach-Object { [string]$_.name })
$statusSummary = @(
    $steps | Where-Object { $_.name -like 'status*' } | ForEach-Object {
        @($_.output_tail | Where-Object { $_ -match 'latest_ok:' -or $_ -match 'latest_ok_reason:' -or $_ -match 'latest_ok_reason_bridge:' -or $_ -match 'task_found:' -or $_ -match 'task_last_result:' -or $_ -match 'pass:' })
    }
)

$payload = [ordered]@{
    ts = $runTs
    ok = $ok
    ok_reason = $okReason
    task_name = $TaskName
    interval_minutes = [int]$IntervalMinutes
    keep_installed = [bool]$KeepInstalled
    latest_json_file = $LatestJsonFile
    history_jsonl = $HistoryJsonl
    failed_step_count = $failed.Count
    failed_steps = $failedStepNames
    status_summary = $statusSummary
    steps = $steps.ToArray()
}

($payload | ConvertTo-Json -Depth 10) | Set-Content -Path $LatestJsonFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8
try {
    $historyLines = Get-Content -Path $HistoryJsonl
    if ($historyLines.Count -gt $MaxHistoryLines) {
        $historyLines | Select-Object -Last $MaxHistoryLines | Set-Content -Path $HistoryJsonl -Encoding UTF8
    }
}
catch {
}

Write-Host "=== RPG Full Health Chain Task Lifecycle ===" -ForegroundColor Cyan
Write-Host "ok: $ok" -ForegroundColor Gray
Write-Host "ok_reason: $okReason" -ForegroundColor Gray
Write-Host "failed_step_count: $($failed.Count)" -ForegroundColor Gray
Write-Host "keep_installed: $KeepInstalled" -ForegroundColor Gray

if ($statusSummary.Count -gt 0) {
    Write-Host "--- status_summary ---" -ForegroundColor Cyan
    $statusSummary | ForEach-Object { Write-Host $_ }
}

if ($ok) {
    Write-Host "[OK] rpg full health chain task lifecycle completed" -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] rpg full health chain task lifecycle failed" -ForegroundColor Red
$failed | ForEach-Object {
    Write-Host ("[FAILED] {0} exit={1}" -f $_.name, $_.exit_code) -ForegroundColor Red
}
exit 1
