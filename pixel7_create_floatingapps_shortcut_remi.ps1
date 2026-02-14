# Pixel 7a: create a HOME shortcut for Remi wallpaper inside Floating Apps
# Tries to:
# 1) Open Floating Apps with Remi URL
# 2) Open window menu
# 3) Tap "デスクトップとして指定" (optional)
# 4) Tap "ショートカットを作成" and confirm "追加"

$ErrorActionPreference = 'SilentlyContinue'

$PREFERRED_TCP = '100.84.2.125:5555'
$URL = 'http://100.73.247.100:5050/remi-wallpaper/remi-pixel7-2026'

$PKG = 'com.lwi.android.flapps'
$ACT = 'com.lwi.android.flapps/.activities.ActivitySplash'

function Get-ActiveDevice {
  adb start-server | Out-Null
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
  Write-Host 'No adb device found. Connect Pixel (USB) or enable Wi-Fi ADB.' -ForegroundColor Red
  exit 1
}

function A([string[]]$Args) {
  & adb -s $DEVICE @Args
}

function CenterFromBounds([string]$b) {
  # bounds format: [x1,y1][x2,y2]
  if ($b -match '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {
    $x1=[int]$Matches[1]; $y1=[int]$Matches[2]; $x2=[int]$Matches[3]; $y2=[int]$Matches[4]
    return @([int](($x1+$x2)/2), [int](($y1+$y2)/2))
  }
  return $null
}

function Dump-UI([string]$localPath) {
  A @('shell','uiautomator','dump','/sdcard/ua.xml') | Out-Null
  A @('pull','/sdcard/ua.xml',$localPath) | Out-Null
}

function Find-NodeByTextOrDesc($xml, [string[]]$needles) {
  $nodes = @($xml.SelectNodes('//node'))
  foreach ($n in $nodes) {
    $t = [string]$n.GetAttribute('text')
    $d = [string]$n.GetAttribute('content-desc')
    foreach ($needle in $needles) {
      if (($t -and $t.Contains($needle)) -or ($d -and $d.Contains($needle))) {
        return $n
      }
    }
  }
  return $null
}

function Tap-Node($node) {
  $b = [string]$node.GetAttribute('bounds')
  $c = CenterFromBounds $b
  if ($c) {
    A @('shell','input','tap',"$($c[0])","$($c[1])") | Out-Null
    Start-Sleep -Milliseconds 600
    return $true
  }
  return $false
}

Write-Host "Using adb device: $DEVICE" -ForegroundColor Gray
A @('wait-for-device') | Out-Null

# Step 1: Open Floating Apps with URL
Write-Host '[1/4] Opening Floating Apps with Remi URL...' -ForegroundColor Cyan
A @('shell','am','start','-n',$ACT,'-a','android.intent.action.VIEW','-d',$URL) | Out-Null
Start-Sleep -Seconds 1
A @('shell','monkey','-p',$PKG,'-c','android.intent.category.LAUNCHER','1') | Out-Null
Start-Sleep -Seconds 1

# Step 2: Open menu and click items
$work = Join-Path $PSScriptRoot 'tmp'
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Path $work -Force | Out-Null }
$ui = Join-Path $work 'ua.xml'

function Open-Menu {
  Dump-UI $ui
  [xml]$x = Get-Content $ui

  # Try common menu buttons / content-desc
  $menuNode = Find-NodeByTextOrDesc $x @('Window menu','ウィンドウ','メニュー','More options','その他のオプション')
  if ($menuNode) { return (Tap-Node $menuNode) }

  # Fallback: tap top-right area (3-dots often live here)
  A @('shell','input','tap','1010','160') | Out-Null
  Start-Sleep -Milliseconds 600
  return $true
}

Write-Host '[2/4] Opening Floating Apps menu...' -ForegroundColor Cyan
Open-Menu | Out-Null

Write-Host '[3/4] Selecting desktop mode + creating shortcut...' -ForegroundColor Cyan

$maxScroll = 7
for ($i=0; $i -lt $maxScroll; $i++) {
  Dump-UI $ui
  [xml]$x = Get-Content $ui

  $desktop = Find-NodeByTextOrDesc $x @('デスクトップとして指定')
  if ($desktop) { Tap-Node $desktop | Out-Null }

  $shortcut = Find-NodeByTextOrDesc $x @('ショートカットを作成','ショートカット作成')
  if ($shortcut) {
    Tap-Node $shortcut | Out-Null
    break
  }

  # scroll menu list
  A @('shell','input','swipe','540','1900','540','900','350') | Out-Null
  Start-Sleep -Milliseconds 600
}

# Confirm add shortcut dialog (Android)
Write-Host '[4/4] Confirming "追加" if prompted...' -ForegroundColor Cyan
for ($j=0; $j -lt 5; $j++) {
  Dump-UI $ui
  [xml]$x = Get-Content $ui
  $add = Find-NodeByTextOrDesc $x @('追加','ADD')
  if ($add) {
    Tap-Node $add | Out-Null
    break
  }
  Start-Sleep -Milliseconds 500
}

A @('shell','input','keyevent','KEYCODE_HOME') | Out-Null
Write-Host 'Done. Check the home screen for the new Remi shortcut icon.' -ForegroundColor Green
Write-Host "If you do not see it: open Floating Apps -> menu -> (Create shortcut) manually." -ForegroundColor Gray
