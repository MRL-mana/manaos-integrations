param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$r12Uninstall = Join-Path $scriptDir "uninstall_r12_health_watch_task.ps1"
$rlUninstall = Join-Path $scriptDir "uninstall_rl_anything_bootstrap_task.ps1"
$r12Status = Join-Path $scriptDir "status_r12_health_watch_task.ps1"
$rlStatus = Join-Path $scriptDir "status_rl_anything_bootstrap_task.ps1"

Write-Host "=== Cleanup R12 + RL Operations ===" -ForegroundColor Cyan

pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Uninstall
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlUninstall

Write-Host "" 
Write-Host "=== Verify Unregistered ===" -ForegroundColor Cyan
pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Status
if ($LASTEXITCODE -ne 0) {
    Write-Host "[OK] R12 task not found (expected)" -ForegroundColor Green
}
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlStatus
if ($LASTEXITCODE -ne 0) {
    Write-Host "[OK] RL task not found (expected)" -ForegroundColor Green
}
