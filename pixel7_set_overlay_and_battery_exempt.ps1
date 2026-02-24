# Pixel 7a: allow overlay + battery exemption for Remi
# - Enables SYSTEM_ALERT_WINDOW appop for Floating Apps
# - Adds packages to device idle whitelist (battery optimizations exempt)

param(
  [string]$DeviceSerial = "",
  [switch]$KeepScreenAwakeWhileCharging
)

$ErrorActionPreference = 'Stop'

$PREFERRED_TCP = '100.84.2.125:5555'
$FLOATING_PKG = 'com.lwi.android.flapps'
$HTTP_SHORTCUTS_PKG = 'ch.rmy.android.http_shortcuts'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
  Write-Host ("adb.exe が見つかりません: {0}" -f $adbExe) -ForegroundColor Red
  exit 1
}

function Get-DevicesText { return (& $adbExe devices | Out-String) }

function Get-DefaultSerial {
  $txt = Get-DevicesText

  if ($env:PIXEL7_ADB_SERIAL -and ($txt -match ([regex]::Escape($env:PIXEL7_ADB_SERIAL) + '\s+device'))) {
    return $env:PIXEL7_ADB_SERIAL
  }

  # Prefer known wireless endpoint
  if ($txt -match ([regex]::Escape($PREFERRED_TCP) + '\s+device')) {
    return $PREFERRED_TCP
  }

  $wirelessLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
      $_ -match '^[0-9.]+:5555\s+device$'
    } | Select-Object -First 1)
  if ($wirelessLine) {
    return ($wirelessLine -replace '\s+device$','')
  }

  $usbLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
      $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
    } | Select-Object -First 1)
  if ($usbLine) {
    return ($usbLine -replace '\s+device$','')
  }

  return ""
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
  $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
  Write-Host 'デバイスが見つかりません。先にADB接続（USB/無線）を確認してください。' -ForegroundColor Yellow
  Write-Host (Get-DevicesText) -ForegroundColor Gray
  exit 2
}

function Run-Adb([string[]]$AdbArgs) {
  & $adbExe -s $DeviceSerial @AdbArgs
}

Write-Host '=== Pixel7 Overlay + Battery Exempt Setup ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray

Write-Host "[1/4] Checking device..." -ForegroundColor Cyan
Run-Adb @('get-state') | Out-Null

Write-Host "[2/4] Allow overlay (SYSTEM_ALERT_WINDOW) for Floating Apps..." -ForegroundColor Cyan
Run-Adb @('shell','appops','set',$FLOATING_PKG,'SYSTEM_ALERT_WINDOW','allow') | Out-Null

Write-Host "[3/4] Exempt from battery optimizations (deviceidle whitelist)..." -ForegroundColor Cyan
Run-Adb @('shell','dumpsys','deviceidle','whitelist',("+{0}" -f $FLOATING_PKG)) | Out-Null
Run-Adb @('shell','dumpsys','deviceidle','whitelist',("+{0}" -f $HTTP_SHORTCUTS_PKG)) | Out-Null

if ($KeepScreenAwakeWhileCharging) {
  Write-Host "[3.5/4] Keep screen awake while charging..." -ForegroundColor Cyan
  Run-Adb @('shell','settings','put','global','stay_on_while_plugged_in','3') | Out-Null
  Run-Adb @('shell','settings','put','system','screen_off_timeout','2147483647') | Out-Null
} else {
  Write-Host "[3.5/4] Skip stay-awake settings (use -KeepScreenAwakeWhileCharging to enable)" -ForegroundColor DarkGray
}

Write-Host "[4/4] Verify..." -ForegroundColor Cyan
$overlay = Run-Adb @('shell','appops','get',$FLOATING_PKG,'SYSTEM_ALERT_WINDOW')
$wl = Run-Adb @('shell','dumpsys','deviceidle','whitelist')

Write-Host "Overlay appop:" -ForegroundColor Gray
$overlay
Write-Host "\nWhitelist contains:" -ForegroundColor Gray
$wl | Select-String -Pattern $FLOATING_PKG,$HTTP_SHORTCUTS_PKG

Write-Host "\nDone." -ForegroundColor Green
