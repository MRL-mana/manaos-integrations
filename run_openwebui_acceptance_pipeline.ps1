param(
    [switch]$SkipAutomated,

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case1 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case2 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case3 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case4 = "skip",

    [string]$Notes = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$autoScript = Join-Path $scriptDir "run_openwebui_tool_acceptance_and_report.ps1"
$recordScript = Join-Path $scriptDir "record_openwebui_manual_cases.ps1"
$finalizeScript = Join-Path $scriptDir "finalize_openwebui_acceptance.ps1"
$optionalEnsureScript = Join-Path $scriptDir "ensure_optional_services.ps1"

Write-Host "=== OpenWebUI Acceptance Pipeline ===" -ForegroundColor Cyan

if (-not (Test-Path $recordScript)) {
    throw "record_openwebui_manual_cases.ps1 not found"
}
if (-not (Test-Path $finalizeScript)) {
    throw "finalize_openwebui_acceptance.ps1 not found"
}
if (-not (Test-Path $optionalEnsureScript)) {
    throw "ensure_optional_services.ps1 not found"
}

Write-Host "`n[0/3] Ensure optional services" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $optionalEnsureScript
if ($LASTEXITCODE -ne 0) {
    throw "Optional services ensure failed (exit=$LASTEXITCODE)"
}

if (-not $SkipAutomated) {
    if (-not (Test-Path $autoScript)) {
        throw "run_openwebui_tool_acceptance_and_report.ps1 not found"
    }

    Write-Host "`n[1/3] Automated acceptance run" -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File $autoScript
    if ($LASTEXITCODE -ne 0) {
        throw "Automated acceptance failed (exit=$LASTEXITCODE)"
    }
}
else {
    Write-Host "`n[1/3] Automated acceptance skipped" -ForegroundColor Yellow
}

Write-Host "`n[2/3] Manual case recording" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File $recordScript -Case1 $Case1 -Case2 $Case2 -Case3 $Case3 -Case4 $Case4 -Notes $Notes
if ($LASTEXITCODE -ne 0) {
    throw "Manual case recording failed (exit=$LASTEXITCODE)"
}

Write-Host "`n[3/3] Final summary generation" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File $finalizeScript
if ($LASTEXITCODE -ne 0) {
    throw "Finalization failed (exit=$LASTEXITCODE)"
}

Write-Host "`n[OK] Acceptance pipeline completed" -ForegroundColor Green
