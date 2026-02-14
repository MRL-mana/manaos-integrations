# Pixel 7a: allow overlay + battery exemption for Remi
# - Enables SYSTEM_ALERT_WINDOW appop for Floating Apps
# - Adds packages to device idle whitelist (battery optimizations exempt)

$ErrorActionPreference = 'SilentlyContinue'

$PREFERRED_TCP = '100.84.2.125:5555'
$FLOATING_PKG = 'com.lwi.android.flapps'
$HTTP_SHORTCUTS_PKG = 'ch.rmy.android.http_shortcuts'

function Get-ActiveDevice {
  $lines = adb devices | Select-Object -Skip 1
  $devices = @()
  foreach ($l in $lines) {
    if (-not $l) { continue }
    if ($l -match '^([^\s]+)\s+device\s*$') { $devices += $Matches[1] }
  }
  if ($devices.Count -eq 0) { return $null }
  if ($devices -contains $PREFERRED_TCP) { return $PREFERRED_TCP }
  $tcp = $devices | Where-Object { $_ -like '*:*' } | Select-Object -First 1
  if ($tcp) { return $tcp }
  return $devices[0]
}

$DEVICE = Get-ActiveDevice
if (-not $DEVICE) {
  Write-Host "No adb device found. Connect Pixel (USB) or enable Wi-Fi ADB." -ForegroundColor Red
  exit 1
}

function Run-Adb([string[]]$AdbArgs) {
  & adb -s $DEVICE @AdbArgs
}

Write-Host "Using adb device: $DEVICE" -ForegroundColor Gray
Write-Host "[1/4] Checking device..." -ForegroundColor Cyan
Run-Adb @('get-state') | Out-Null

Write-Host "[2/4] Allow overlay (SYSTEM_ALERT_WINDOW) for Floating Apps..." -ForegroundColor Cyan
Run-Adb @('shell','appops','set',$FLOATING_PKG,'SYSTEM_ALERT_WINDOW','allow') | Out-Null

Write-Host "[3/4] Exempt from battery optimizations (deviceidle whitelist)..." -ForegroundColor Cyan
Run-Adb @('shell','dumpsys','deviceidle','whitelist','+'.$FLOATING_PKG) | Out-Null
Run-Adb @('shell','dumpsys','deviceidle','whitelist','+'.$HTTP_SHORTCUTS_PKG) | Out-Null

# Optional: keep screen awake while charging (helps prevent lock interruptions)
Write-Host "[3.5/4] (Optional) Keep screen awake while charging..." -ForegroundColor Cyan
Run-Adb @('shell','settings','put','global','stay_on_while_plugged_in','3') | Out-Null
Run-Adb @('shell','settings','put','system','screen_off_timeout','2147483647') | Out-Null

Write-Host "[4/4] Verify..." -ForegroundColor Cyan
$overlay = Run-Adb @('shell','appops','get',$FLOATING_PKG,'SYSTEM_ALERT_WINDOW')
$wl = Run-Adb @('shell','dumpsys','deviceidle','whitelist')

Write-Host "Overlay appop:" -ForegroundColor Gray
$overlay
Write-Host "\nWhitelist contains:" -ForegroundColor Gray
$wl | Select-String -Pattern $FLOATING_PKG,$HTTP_SHORTCUTS_PKG

Write-Host "\nDone." -ForegroundColor Green
