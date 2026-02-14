# Pixel 7a: one-command restore for Remi (PC + Android)
# - Starts/ensures Remi API is running on PC
# - Ensures overlay + battery exemptions on Pixel
# - Opens Remi inside Floating Apps

$ErrorActionPreference = 'Stop'

function Step($msg) {
  Write-Host $msg -ForegroundColor Cyan
}

$root = $PSScriptRoot

Step "[1/3] Ensuring Remi API is running on PC..."
$startApi = Join-Path $root 'start_remi_api.ps1'
if (Test-Path $startApi) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File $startApi
} else {
  Write-Host "Missing: $startApi" -ForegroundColor Yellow
}

Step "[2/3] Ensuring Pixel overlay permission + battery exemptions..."
$setPerms = Join-Path $root 'pixel7_set_overlay_and_battery_exempt.ps1'
if (Test-Path $setPerms) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File $setPerms
} else {
  Write-Host "Missing: $setPerms" -ForegroundColor Yellow
}

Step "[3/3] Opening Remi overlay on Pixel..."
$openOverlay = Join-Path $root 'pixel7_open_remi_overlay.ps1'
if (Test-Path $openOverlay) {
  pwsh -NoProfile -ExecutionPolicy Bypass -File $openOverlay
  if ($LASTEXITCODE -eq 2) {
    Write-Host "Pixel is locked. Unlock it and re-run: .\\pixel7_remi_restore.ps1" -ForegroundColor Yellow
  }
} else {
  Write-Host "Missing: $openOverlay" -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Green
