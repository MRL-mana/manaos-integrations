param(
    [string]$ConfigFile = "",
    [switch]$IncludeCheckScripts,
    [int]$NotifyFailureCooldownMinutes = 60,
    [int]$WaitAfterRunSeconds = 6
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}

$notifyFlowScript = Join-Path $scriptDir "test_reason_enum_lint_notify_flow.ps1"
$cooldownVerifyScript = Join-Path $scriptDir "verify_reason_enum_lint_cooldown.ps1"
$statusScript = Join-Path $scriptDir "status_reason_enum_lint_task.ps1"

foreach ($required in @($notifyFlowScript, $cooldownVerifyScript, $statusScript)) {
    if (-not (Test-Path $required)) {
        throw "Required script not found: $required"
    }
}

Write-Host "=== Full Chain 1/3: Notify Flow Test ===" -ForegroundColor Yellow
$notifyArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$notifyFlowScript,'-ConfigFile',$ConfigFile)
if ($IncludeCheckScripts.IsPresent) {
    $notifyArgs += '-IncludeCheckScripts'
}
& pwsh @notifyArgs
$notifyExit = $LASTEXITCODE
Write-Host "notify_flow_exit=$notifyExit" -ForegroundColor Gray
if ($notifyExit -ne 0) {
    throw "Notify flow test failed (exit=$notifyExit)"
}

Write-Host "=== Full Chain 2/3: Cooldown Verify ===" -ForegroundColor Yellow
$cooldownArgs = @(
    '-NoProfile','-ExecutionPolicy','Bypass','-File',$cooldownVerifyScript,
    '-ConfigFile',$ConfigFile,
    '-NotifyFailureCooldownMinutes',"$NotifyFailureCooldownMinutes",
    '-WaitAfterRunSeconds',"$WaitAfterRunSeconds"
)
& pwsh @cooldownArgs
$cooldownExit = $LASTEXITCODE
Write-Host "cooldown_verify_exit=$cooldownExit" -ForegroundColor Gray
if ($cooldownExit -ne 0) {
    throw "Cooldown verification failed (exit=$cooldownExit)"
}

Write-Host "=== Full Chain 3/3: Final Status Snapshot ===" -ForegroundColor Yellow
$statusOutput = & pwsh -NoProfile -ExecutionPolicy Bypass -File $statusScript
$statusOutput | Select-String "latest_ok:|latest_ok_reason:|latest_failure_notify_attempted:|latest_failure_notified:|latest_failure_notify_suppressed_reason:|state_last_status:|state_last_failure_notified_at:" | ForEach-Object {
    Write-Host $_.Line
}

Write-Host "[OK] reason lint full chain test passed" -ForegroundColor Green
exit 0
