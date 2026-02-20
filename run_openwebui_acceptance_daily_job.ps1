param(
    [switch]$SkipNotify
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pipelineScript = Join-Path $scriptDir "run_openwebui_acceptance_pipeline_full_auto.ps1"
$strictCheckScript = Join-Path $scriptDir "check_latest_openwebui_acceptance.ps1"
$notifyScript = Join-Path $scriptDir "notify_openwebui_acceptance_pass.ps1"

if (-not (Test-Path $pipelineScript)) { throw "Missing script: $pipelineScript" }
if (-not (Test-Path $strictCheckScript)) { throw "Missing script: $strictCheckScript" }
if ((-not $SkipNotify) -and (-not (Test-Path $notifyScript))) { throw "Missing script: $notifyScript" }

Write-Host "=== OpenWebUI Acceptance Daily Job ===" -ForegroundColor Cyan

Write-Host "[1/3] Run full-auto acceptance pipeline" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $pipelineScript
if ($LASTEXITCODE -ne 0) {
    throw "Full-auto acceptance pipeline failed (exit=$LASTEXITCODE)"
}

Write-Host "[2/3] Verify strict PASS verdict" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $strictCheckScript -RequirePass
if ($LASTEXITCODE -ne 0) {
    throw "Strict PASS verification failed (exit=$LASTEXITCODE)"
}

if (-not $SkipNotify) {
    Write-Host "[3/3] Notify latest verdict" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WriteStatusFile
    if ($LASTEXITCODE -ne 0) {
        throw "Verdict notification failed (exit=$LASTEXITCODE)"
    }
}
else {
    Write-Host "[3/3] Notify latest verdict skipped" -ForegroundColor Yellow
}

Write-Host "[OK] OpenWebUI acceptance daily job completed" -ForegroundColor Green
exit 0
