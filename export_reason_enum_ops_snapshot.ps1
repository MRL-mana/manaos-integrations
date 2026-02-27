param(
    [string]$OutputFile = "",
    [string]$HistoryJsonl = "",
    [string]$LintConfigFile = "",
    [string]$CooldownVerifyStatusScript = "",
    [string]$LifecycleStatusScript = "",
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($OutputFile)) {
    $OutputFile = Join-Path $scriptDir "logs\reason_enum_ops_snapshot.latest.json"
}
if ([string]::IsNullOrWhiteSpace($HistoryJsonl)) {
    $HistoryJsonl = Join-Path $scriptDir "logs\reason_enum_ops_snapshot.history.jsonl"
}
if ([string]::IsNullOrWhiteSpace($LintConfigFile)) {
    $LintConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}
if ([string]::IsNullOrWhiteSpace($CooldownVerifyStatusScript)) {
    $CooldownVerifyStatusScript = Join-Path $scriptDir "status_reason_enum_lint_cooldown_verify_task.ps1"
}
if ([string]::IsNullOrWhiteSpace($LifecycleStatusScript)) {
    $LifecycleStatusScript = Join-Path $scriptDir "status_reason_enum_lint_cooldown_lifecycle.ps1"
}

function Invoke-StatusJson {
    param(
        [string]$ScriptPath,
        [string[]]$ScriptArgs
    )

    if (-not (Test-Path $ScriptPath)) {
        return [ordered]@{
            ok = $false
            ok_reason = 'script_missing'
            script = $ScriptPath
            exit_code = -1
            data = $null
        }
    }

    $cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) + $ScriptArgs
    $output = @(& pwsh @cmdArgs 2>&1 | ForEach-Object { [string]$_ })
    $exitCode = $LASTEXITCODE
    $joinedText = ($output -join [Environment]::NewLine)
    $startIndex = $joinedText.IndexOf('{')
    $endIndex = $joinedText.LastIndexOf('}')
    $jsonText = ""
    if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
        $jsonText = $joinedText.Substring($startIndex, ($endIndex - $startIndex + 1))
    }
    else {
        $jsonText = $joinedText
    }

    try {
        $data = $jsonText | ConvertFrom-Json
        return [ordered]@{
            ok = ($exitCode -eq 0)
            ok_reason = if ($exitCode -eq 0) { 'ok' } else { 'status_exit_nonzero' }
            script = $ScriptPath
            exit_code = [int]$exitCode
            data = $data
        }
    }
    catch {
        return [ordered]@{
            ok = $false
            ok_reason = 'status_json_parse_failed'
            script = $ScriptPath
            exit_code = [int]$exitCode
            data = $null
            output_tail = @($output | Select-Object -Last 20)
        }
    }
}

$runTs = [datetimeoffset]::Now.ToString('o')

$lintPayload = [ordered]@{
    config_file = $LintConfigFile
    config_found = $false
    latest_json_file = ""
    notify_state_file = ""
    latest_ts = 'N/A'
    latest_ok = $false
    latest_ok_reason = 'source_missing'
    latest_failure_notify_suppressed_reason = 'source_missing'
    state_last_status = ""
    state_updated_at = ""
}

if (Test-Path $LintConfigFile) {
    $lintPayload.config_found = $true
    try {
        $cfg = Get-Content -Path $LintConfigFile -Raw | ConvertFrom-Json
        $latestJson = [string]$cfg.latest_json_file
        $notifyStateFile = [string]$cfg.notify_state_file
        $lintPayload.latest_json_file = $latestJson
        $lintPayload.notify_state_file = $notifyStateFile

        if (-not [string]::IsNullOrWhiteSpace($latestJson) -and (Test-Path $latestJson)) {
            try {
                $latest = Get-Content -Path $latestJson -Raw | ConvertFrom-Json
                $lintPayload.latest_ts = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ts)) { [string]$latest.ts } else { 'N/A' }
                $lintPayload.latest_ok = if ($null -ne $latest.ok) { [bool]$latest.ok } else { $false }
                $lintPayload.latest_ok_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.ok_reason)) { [string]$latest.ok_reason } else { 'source_missing' }
                $lintPayload.latest_failure_notify_suppressed_reason = if (-not [string]::IsNullOrWhiteSpace([string]$latest.failure_notify_suppressed_reason)) { [string]$latest.failure_notify_suppressed_reason } else { '' }
            }
            catch {
                $lintPayload.latest_ok = $false
                $lintPayload.latest_ok_reason = 'source_missing'
                $lintPayload.latest_failure_notify_suppressed_reason = 'source_missing'
            }
        }

        if (-not [string]::IsNullOrWhiteSpace($notifyStateFile) -and (Test-Path $notifyStateFile)) {
            try {
                $state = Get-Content -Path $notifyStateFile -Raw | ConvertFrom-Json
                $lintPayload.state_last_status = [string]$state.last_status
                $lintPayload.state_updated_at = [string]$state.updated_at
            }
            catch {
            }
        }
    }
    catch {
        $lintPayload.config_found = $false
        $lintPayload.latest_ok = $false
        $lintPayload.latest_ok_reason = 'source_missing'
    }
}

$cooldownVerifyResult = Invoke-StatusJson -ScriptPath $CooldownVerifyStatusScript -ScriptArgs @('-AsJson')
$lifecycleResult = Invoke-StatusJson -ScriptPath $LifecycleStatusScript -ScriptArgs @('-AsJson')

$cooldownVerifyLatestOk = $false
if ($null -ne $cooldownVerifyResult.data -and $null -ne $cooldownVerifyResult.data.latest_ok) {
    $cooldownVerifyLatestOk = [bool]$cooldownVerifyResult.data.latest_ok
}
$lifecycleLatestOk = $false
if ($null -ne $lifecycleResult.data -and $null -ne $lifecycleResult.data.latest_ok) {
    $lifecycleLatestOk = [bool]$lifecycleResult.data.latest_ok
}

$overallOk = ([bool]$lintPayload.latest_ok -and $cooldownVerifyLatestOk -and $lifecycleLatestOk -and $cooldownVerifyResult.ok -and $lifecycleResult.ok)
$overallReason = if ($overallOk) { 'ops_snapshot_passed' } else { 'ops_snapshot_failed' }

$cooldownVerifyOutputTail = @()
if ($cooldownVerifyResult.PSObject.Properties.Name -contains 'output_tail' -and $null -ne $cooldownVerifyResult.output_tail) {
    $cooldownVerifyOutputTail = @($cooldownVerifyResult.output_tail)
}

$lifecycleOutputTail = @()
if ($lifecycleResult.PSObject.Properties.Name -contains 'output_tail' -and $null -ne $lifecycleResult.output_tail) {
    $lifecycleOutputTail = @($lifecycleResult.output_tail)
}

$payload = [ordered]@{
    ts = $runTs
    ok = $overallOk
    ok_reason = $overallReason
    output_file = $OutputFile
    history_jsonl = $HistoryJsonl
    lint = $lintPayload
    cooldown_verify = [ordered]@{
        status_ok = [bool]$cooldownVerifyResult.ok
        status_ok_reason = [string]$cooldownVerifyResult.ok_reason
        exit_code = [int]$cooldownVerifyResult.exit_code
        script = [string]$cooldownVerifyResult.script
        output_tail = $cooldownVerifyOutputTail
        latest = $cooldownVerifyResult.data
    }
    lifecycle = [ordered]@{
        status_ok = [bool]$lifecycleResult.ok
        status_ok_reason = [string]$lifecycleResult.ok_reason
        exit_code = [int]$lifecycleResult.exit_code
        script = [string]$lifecycleResult.script
        output_tail = $lifecycleOutputTail
        latest = $lifecycleResult.data
    }
}

$outDir = Split-Path -Parent $OutputFile
if (-not [string]::IsNullOrWhiteSpace($outDir) -and -not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$historyDir = Split-Path -Parent $HistoryJsonl
if (-not [string]::IsNullOrWhiteSpace($historyDir) -and -not (Test-Path $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
}

($payload | ConvertTo-Json -Depth 10) | Set-Content -Path $OutputFile -Encoding UTF8
($payload | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $HistoryJsonl -Encoding UTF8

if ($AsJson) {
    Write-Output ($payload | ConvertTo-Json -Depth 10)
}
else {
    Write-Host "=== Reason Enum Ops Snapshot Export ===" -ForegroundColor Cyan
    Write-Host "ok: $overallOk" -ForegroundColor Gray
    Write-Host "ok_reason: $overallReason" -ForegroundColor Gray
    Write-Host "output_file: $OutputFile" -ForegroundColor Gray
    Write-Host "history_jsonl: $HistoryJsonl" -ForegroundColor Gray
    Write-Host "lint.latest_ok_reason: $($lintPayload.latest_ok_reason)" -ForegroundColor Gray
    Write-Host "cooldown_verify.status_ok_reason: $($cooldownVerifyResult.ok_reason)" -ForegroundColor Gray
    Write-Host "lifecycle.status_ok_reason: $($lifecycleResult.ok_reason)" -ForegroundColor Gray
}

if ($overallOk) {
    exit 0
}

exit 1
