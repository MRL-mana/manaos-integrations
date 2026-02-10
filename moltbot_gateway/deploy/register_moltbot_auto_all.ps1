# Register Moltbot auto-start + auto-heal + daily list_only (all at once)
# Run from repo root: .\moltbot_gateway\deploy\register_moltbot_auto_all.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..")).Path
Set-Location $repoRoot

Write-Host "=== Moltbot auto-start + daily list_only ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Moltbot Gateway logon start..."
& (Join-Path $scriptDir "register_gateway_autostart.ps1")
Write-Host ""

$openclawScript = Join-Path $scriptDir "register_openclaw_gateway_autostart.ps1"
if (Test-Path $openclawScript) {
    Write-Host "[2/4] OpenClaw Gateway logon start..."
    & $openclawScript
} else {
    Write-Host "[2/4] OpenClaw script not found (skip)"
}
Write-Host ""

Write-Host "[3/4] Heal every 5 min..."
& (Join-Path $scriptDir "register_heal_manaos_services_every5min.ps1")
Write-Host ""

Write-Host "[4/4] Daily list_only..."
& (Join-Path $scriptDir "register_moltbot_daily_list_only.ps1")
Write-Host ""

Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "To disable/remove: see each script output."
