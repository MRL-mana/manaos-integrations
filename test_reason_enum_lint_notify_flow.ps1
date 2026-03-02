param(
    [string]$ConfigFile = "",
    [switch]$IncludeCheckScripts
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\reason_enum_lint_task.config.json"
}

$runScript = Join-Path $scriptDir "run_reason_enum_lint_once.ps1"
$statusScript = Join-Path $scriptDir "status_reason_enum_lint_task.ps1"

if (-not (Test-Path $runScript)) {
    throw "Run script not found: $runScript"
}
if (-not (Test-Path $statusScript)) {
    throw "Status script not found: $statusScript"
}

function Show-StatusSummary {
    param([string]$Title)

    Write-Host "=== $Title ===" -ForegroundColor Cyan
    $output = & pwsh -NoProfile -ExecutionPolicy Bypass -File $statusScript
    $output | Select-String "latest_ok:|latest_ok_reason:|latest_failure_notify_attempted:|latest_failure_notified:|latest_failure_notify_suppressed_reason:|state_last_status:|state_last_failure_notified_at:" | ForEach-Object {
        Write-Host $_.Line
    }
}

$commonArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$runScript,'-ConfigFile',$ConfigFile)
if ($IncludeCheckScripts.IsPresent) {
    $commonArgs += '-IncludeCheckScripts'
}

Write-Host "=== Step 1/3: Simulate failure run ===" -ForegroundColor Yellow
$failArgs = @($commonArgs) + '-SimulateFailure'
& pwsh @failArgs
$failExit = $LASTEXITCODE
Write-Host "simulate_failure_exit=$failExit" -ForegroundColor Gray
Show-StatusSummary -Title "Status After SimulateFailure"

Write-Host "=== Step 2/3: Normal lint run ===" -ForegroundColor Yellow
& pwsh @commonArgs
$okExit = $LASTEXITCODE
Write-Host "normal_run_exit=$okExit" -ForegroundColor Gray
Show-StatusSummary -Title "Status After Normal Run"

Write-Host "=== Step 3/3: Verdict ===" -ForegroundColor Yellow
if ($failExit -eq 2 -and $okExit -eq 0) {
    Write-Host "[OK] reason lint notify flow test passed" -ForegroundColor Green
    exit 0
}

Write-Host "[ALERT] reason lint notify flow test failed" -ForegroundColor Red
exit 1
