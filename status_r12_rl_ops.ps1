param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$r12Status = Join-Path $scriptDir "status_r12_health_watch_task.ps1"
$rlStatus = Join-Path $scriptDir "status_rl_anything_bootstrap_task.ps1"
$r12Log = Join-Path $scriptDir "logs\r12_health_watch_task.jsonl"

Write-Host "=== Combined Ops Status (R12 + RL) ===" -ForegroundColor Cyan

pwsh -NoProfile -ExecutionPolicy Bypass -File $r12Status
pwsh -NoProfile -ExecutionPolicy Bypass -File $rlStatus

if (Test-Path $r12Log) {
    Write-Host "" 
    Write-Host "=== R12 Log Tail (last 20) ===" -ForegroundColor Cyan
    Get-Content $r12Log -Tail 20
} else {
    Write-Host "[INFO] r12 log not found: $r12Log" -ForegroundColor Yellow
}
