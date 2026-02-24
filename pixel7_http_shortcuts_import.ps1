param(
  [string]$Serial = "",
  [string]$PreferredTcp = "100.84.2.125:5555"
)

<#
Pixel 7a: open HTTP Shortcuts import for Remi
- Shares remi_android_shortcuts.json to HTTP Shortcuts ShareActivity
- If the phone is locked (PIN), the UI won't appear; this script waits and prompts to unlock.
- Tries to auto-tap common Import/OK buttons when they are visible.
#>

$ErrorActionPreference = 'SilentlyContinue'

$PREFERRED_TCP = if ([string]::IsNullOrWhiteSpace($PreferredTcp)) { '100.84.2.125:5555' } else { $PreferredTcp }
$SHARE_ACT = 'ch.rmy.android.http_shortcuts/.activities.misc.share.ShareActivity'

function Resolve-AdbExecutable {
  $candidates = @()

  $cmd = Get-Command adb -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source) {
    $candidates += $cmd.Source
  }

  # Prefer scrcpy-bundled adb if present (common in this repo's environment)
  try {
    $scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
    $candidates += (Join-Path $scrcpyDir 'adb.exe')
  } catch {
  }

  if ($env:LOCALAPPDATA) {
    $candidates += (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\adb.exe')
    $candidates += (Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe')
  }

  $candidates += 'C:\Android\platform-tools\adb.exe'
  $candidates += 'C:\platform-tools\adb.exe'
  $candidates += 'C:\adb\adb.exe'

  foreach ($p in ($candidates | Select-Object -Unique)) {
    if ([string]::IsNullOrWhiteSpace($p)) { continue }
    if (Test-Path $p) { return $p }
  }

  return $null
}

function Invoke-Adb {
  param(
    [Parameter(Mandatory = $true)][string[]]$Args
  )
  if ($null -eq $script:AdbExe) { throw 'adb executable not resolved' }
  return (& $script:AdbExe @Args)
}

function Get-ActiveDevice {
  $lines = Invoke-Adb @('devices') | Select-Object -Skip 1
  $devices = @()
  foreach ($l in $lines) {
    if (-not $l) { continue }
    if ($l -match '^([^\s]+)\s+device\s*$') { $devices += $Matches[1] }
  }
  if ($devices.Count -eq 0) { return $null }
  if (-not [string]::IsNullOrWhiteSpace($Serial) -and ($devices -contains $Serial)) { return $Serial }
  if ($devices -contains $PREFERRED_TCP) { return $PREFERRED_TCP }
  $tcp = $devices | Where-Object { $_ -like '*:*' } | Select-Object -First 1
  if ($tcp) { return $tcp }
  return $devices[0]
}

function Wait-ForDevice {
  Invoke-Adb @('start-server') | Out-Null
  $state = (Invoke-Adb @('-s', $DEVICE, 'get-state') 2>$null)
  if ($LASTEXITCODE -ne 0 -or -not $state) {
    $maybe = Get-ActiveDevice
    if ($maybe) {
      $script:DEVICE = $maybe
      Write-Host "Re-selected adb device: $DEVICE" -ForegroundColor Gray
    }
  }
  Invoke-Adb @('-s', $DEVICE, 'wait-for-device') | Out-Null
}

function Dump-UiXml([string]$name) {
  $remote = "/data/local/tmp/${name}.xml"
  $local = Join-Path $PSScriptRoot "_tmp_${name}.xml"
  Wait-ForDevice
  Invoke-Adb @('-s', $DEVICE, 'shell', 'uiautomator', 'dump', $remote) | Out-Null
  Invoke-Adb @('-s', $DEVICE, 'pull', $remote, $local) | Out-Null
  try { return (Get-Content $local -Raw -ErrorAction SilentlyContinue) } catch { return '' }
}

function Get-CenterFromBounds([string]$bounds) {
  if ($bounds -match '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {
    $x1 = [int]$Matches[1]; $y1 = [int]$Matches[2]
    $x2 = [int]$Matches[3]; $y2 = [int]$Matches[4]
    $cx = [int](($x1 + $x2) / 2)
    $cy = [int](($y1 + $y2) / 2)
    return @($cx,$cy)
  }
  return $null
}

function Find-FirstBoundsByLabels([string]$xml, [string[]]$labels) {
  foreach ($label in $labels) {
    if ($null -eq $label) { continue }
    if ([string]::IsNullOrWhiteSpace($label)) { continue }
    $escaped = [regex]::Escape($label)
    # Only consider actionable nodes to avoid matching large container/root nodes.
    $pattern = '<node[^>]*(?:text="' + $escaped + '"|content-desc="' + $escaped + '")[^>]*clickable="true"[^>]*bounds="([^"]+)"'
    $m = [regex]::Match($xml, $pattern, 'IgnoreCase')
    if ($m.Success) { return $m.Groups[1].Value }
  }
  return $null
}

function Device-LooksLocked([string]$xml) {
  if (-not $xml) { return $false }
  # Prefer resource-id based detection (ASCII-only to avoid encoding issues in Windows PowerShell)
  if ($xml -match 'com\.android\.systemui:id/keyguard_' ) { return $true }
  if ($xml -match 'com\.android\.systemui:id/keyguard_pin_view') { return $true }
  if ($xml -match 'com\.android\.systemui:id/pinEntry') { return $true }
  return $false
}

function Ensure-Unlocked {
  # Wake screen
  Wait-ForDevice
  Invoke-Adb @('-s', $DEVICE, 'shell', 'input', 'keyevent', '224') | Out-Null
  Start-Sleep -Milliseconds 400

  $waited = 0
  while ($waited -lt 180) {
    $xml = Dump-UiXml 'screen'
    if (-not (Device-LooksLocked $xml)) { return $true }
    if ($waited -eq 0) {
      Write-Host 'Device is locked (PIN). Please unlock the Pixel now (fingerprint/PIN)...' -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 1
    $waited++
  }
  return $false
}

function Close-SystemOverlays {
  # Try to close notification shade / overlays
  Wait-ForDevice
  Invoke-Adb @('-s', $DEVICE, 'shell', 'input', 'keyevent', '4') | Out-Null
  Start-Sleep -Milliseconds 250
  Invoke-Adb @('-s', $DEVICE, 'shell', 'input', 'keyevent', '4') | Out-Null
  Start-Sleep -Milliseconds 250
}

function Try-AutoConfirmImport {
  # Keep the script source ASCII-only for Windows PowerShell; build JP labels via code points.
  $jpImport = [string]::Concat([char]0x30A4,[char]0x30F3,[char]0x30DD,[char]0x30FC,[char]0x30C8) # インポート
  $jpConfirm = [string]::Concat([char]0x78BA,[char]0x8A8D) # 確認
  $jpYes = [string]::Concat([char]0x306F,[char]0x3044) # はい
  $jpAllow = [string]::Concat([char]0x8A31,[char]0x53EF) # 許可
  $jpOkFullWidth = [string]::Concat([char]0xFF2F,[char]0xFF2B) # ＯＫ
  $jpImportVerb1 = [string]::Concat([char]0x53D6,[char]0x308A,[char]0x8FBC,[char]0x3080) # 取り込む
  $jpImportVerb2 = [string]::Concat([char]0x8AAD,[char]0x307F,[char]0x8FBC,[char]0x3080) # 読み込む

  $labelsPrimary = @('Import','IMPORT',$jpImport,$jpImportVerb1,$jpImportVerb2)
  $labelsSecondary = @('OK','Ok','ok',$jpOkFullWidth,$jpConfirm,$jpYes,$jpAllow)

  for ($i=0; $i -lt 5; $i++) {
    $xml = Dump-UiXml 'http_shortcuts'
    $bounds = Find-FirstBoundsByLabels $xml $labelsPrimary
    if (-not $bounds) { $bounds = Find-FirstBoundsByLabels $xml $labelsSecondary }
    if ($bounds) {
      $pt = Get-CenterFromBounds $bounds
      if ($pt) {
        Write-Host "Auto-tap: $bounds" -ForegroundColor Gray
        Invoke-Adb @('-s', $DEVICE, 'shell', 'input', 'tap', [string]$pt[0], [string]$pt[1]) | Out-Null
        Start-Sleep -Milliseconds 700
        continue
      }
    }
    Start-Sleep -Milliseconds 500
  }
}

$script:AdbExe = Resolve-AdbExecutable
if ($null -eq $script:AdbExe) {
  Write-Host 'adb was not found. Install Android platform-tools or place adb on PATH (or install scrcpy bundle used by this repo).' -ForegroundColor Red
  exit 10
}

Invoke-Adb @('start-server') | Out-Null
$DEVICE = Get-ActiveDevice
if (-not $DEVICE) {
  Write-Host 'No adb device found. Connect Pixel (USB) or enable Wi-Fi ADB.' -ForegroundColor Red
  exit 1
}

Write-Host "Using adb device: $DEVICE" -ForegroundColor Gray
Invoke-Adb @('-s', $DEVICE, 'wait-for-device') | Out-Null

if (-not (Ensure-Unlocked)) {
  Write-Host 'Still locked. Unlock the phone and re-run.' -ForegroundColor Yellow
  exit 3
}

Close-SystemOverlays

# Ensure file exists (paths may vary; also fails before first unlock after reboot)
$paths = @(
  '/sdcard/Download/remi_android_shortcuts.json',
  '/storage/self/primary/Download/remi_android_shortcuts.json',
  '/storage/emulated/0/Download/remi_android_shortcuts.json'
)
$found = $false
foreach ($p in $paths) {
  $check = Invoke-Adb @('-s', $DEVICE, 'shell', "ls -l $p 2>/dev/null || echo NOT_FOUND")
  if ($check -and ($check -notmatch 'NOT_FOUND')) { $found = $true; break }
}
if (-not $found) {
  Write-Host "Not found on device under Download/: remi_android_shortcuts.json" -ForegroundColor Yellow
  Write-Host 'If the phone was just rebooted: unlock once (PIN), then re-run sync+import.' -ForegroundColor Yellow
  Write-Host 'Otherwise: re-push the JSON from PC and re-run.' -ForegroundColor Yellow
  exit 2
}

# Prefer SAF content URI (with permission grant)
$uri = "content://com.android.externalstorage.documents/document/primary:Download/remi_android_shortcuts.json"
Write-Host 'Opening HTTP Shortcuts import (share JSON)...' -ForegroundColor Cyan
Invoke-Adb @('-s', $DEVICE, 'shell', "am start -a android.intent.action.SEND -t application/json --grant-read-uri-permission --eu android.intent.extra.STREAM '$uri' -n $SHARE_ACT") | Out-Null

Start-Sleep -Milliseconds 800
Close-SystemOverlays
Try-AutoConfirmImport

$xmlAfter = Dump-UiXml 'after_import'
if ($xmlAfter -match 'ch\.rmy\.android\.http_shortcuts:id/widget_label' -and $xmlAfter -match 'Remi') {
  Write-Host 'Detected a Remi HTTP Shortcuts widget on screen. Import may already be complete.' -ForegroundColor Green
}

Write-Host 'Done. If an Import/OK prompt is still visible, confirm it on the Pixel.' -ForegroundColor Green
