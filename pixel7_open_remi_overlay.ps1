# Pixel 7a: open Remi wallpaper inside Floating Apps (app-like)
# Prefer tapping the already-created home shortcut (more reliable than hard-coded activities).

$ErrorActionPreference = 'SilentlyContinue'

$PREFERRED_TCP = '100.84.2.125:5555'
$URL = 'http://100.73.247.100:5050/remi-wallpaper/remi-pixel7-2026'
$SHORTCUT_LABELS = @('Remi','レミ','REMI')
$HOME_PKG = 'com.google.android.apps.nexuslauncher'

Write-Host "Opening Remi overlay..." -ForegroundColor Cyan
adb start-server | Out-Null
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

Write-Host "Using adb device: $DEVICE" -ForegroundColor Gray
adb -s $DEVICE wait-for-device | Out-Null

function Wait-ForDevice {
	adb start-server | Out-Null
	# If the stored serial disappears, re-detect.
	$state = (adb -s $DEVICE get-state 2>$null)
	if ($LASTEXITCODE -ne 0 -or -not $state) {
		$maybe = Get-ActiveDevice
		if ($maybe) {
			$script:DEVICE = $maybe
			Write-Host "Re-selected adb device: $DEVICE" -ForegroundColor Gray
		}
	}
	adb -s $DEVICE wait-for-device | Out-Null
}

function Get-FocusedPackage {
	try {
		$out = adb -s $DEVICE shell "dumpsys window | grep -E 'mCurrentFocus' | head -n 1" 2>$null
		if ($out -match 'mCurrentFocus=Window\{[^\s]+\s+u0\s+([^/]+)/') {
			return $Matches[1]
		}
	} catch {
		# ignore
	}
	return $null
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

function Find-NodeBoundsByLabel([string]$xml, [string]$label) {
	$escaped = [regex]::Escape($label)
	$pattern = '<node[^>]*(?:text="' + $escaped + '"|content-desc="' + $escaped + '")[^>]*bounds="([^"]+)"'
	$m = [regex]::Match($xml, $pattern, 'IgnoreCase')
	if ($m.Success) { return $m.Groups[1].Value }
	return $null
}

# Wake screen (unlock is still manual if PIN/biometric is enabled)
Wait-ForDevice
adb -s $DEVICE shell input keyevent 224 | Out-Null
Start-Sleep -Milliseconds 400

$waited = 0
while ($waited -lt 180) {
	Wait-ForDevice
	$focused = Get-FocusedPackage
	if ($focused -eq $HOME_PKG) { break }
	if ($waited -eq 0) {
		Write-Host "Device appears locked or not on home. Please unlock the Pixel now (fingerprint/PIN)..." -ForegroundColor Yellow
	}
	Start-Sleep -Seconds 1
	$waited++
}

if ((Get-FocusedPackage) -ne $HOME_PKG) {
	Write-Host "Still not on home. Unlock the phone and run again." -ForegroundColor Yellow
	exit 2
}

function Dump-HomeXml {
	$remote = '/data/local/tmp/_remi_home.xml'
	$local = Join-Path $PSScriptRoot '_tmp_remi_home.xml'
	Wait-ForDevice
	adb -s $DEVICE shell uiautomator dump $remote | Out-Null
	adb -s $DEVICE pull $remote $local | Out-Null
	try { return (Get-Content $local -Raw -ErrorAction SilentlyContinue) } catch { return '' }
}

$tapped = $false

function Try-TapShortcut {
	param([string]$xml)
	foreach ($label in $SHORTCUT_LABELS) {
		$bounds = Find-NodeBoundsByLabel $xml $label
		if ($bounds) {
			$pt = Get-CenterFromBounds $bounds
			if ($pt) {
				Write-Host "Tapping home shortcut: $label" -ForegroundColor Cyan
				adb -s $DEVICE shell input tap $pt[0] $pt[1] | Out-Null
				return $true
			}
		}
	}
	return $false
}

# Scan a few home pages (icon may not be on the current page)
$xml = Dump-HomeXml
if (Try-TapShortcut $xml) { $tapped = $true }

if (-not $tapped) {
	for ($i=0; $i -lt 3; $i++) {
		adb -s $DEVICE shell input swipe 900 1200 200 1200 250 | Out-Null
		Start-Sleep -Milliseconds 500
		$xml = Dump-HomeXml
		if (Try-TapShortcut $xml) { $tapped = $true; break }
	}
}

if (-not $tapped) {
	for ($i=0; $i -lt 3; $i++) {
		adb -s $DEVICE shell input swipe 200 1200 900 1200 250 | Out-Null
		Start-Sleep -Milliseconds 500
		$xml = Dump-HomeXml
		if (Try-TapShortcut $xml) { $tapped = $true; break }
	}
}

if (-not $tapped) {
	Write-Host "Remi home shortcut not found." -ForegroundColor Yellow
	Write-Host "Fallback: opening Remi URL in Chrome so you can create the Floating Apps shortcut." -ForegroundColor Yellow
	Write-Host "1) Floating Appsを開く → URLを開く → デスクトップ指定/ショートカット作成" -ForegroundColor Gray
	Write-Host "2) ホームに 'Remi'（またはレミ）アイコンを置く → 次回からこのスクリプトで一発復帰" -ForegroundColor Gray
	adb -s $DEVICE shell "am start -a android.intent.action.VIEW -d '$URL' com.android.chrome" | Out-Null
	Start-Sleep -Milliseconds 600
	adb -s $DEVICE shell "am start -a android.intent.action.VIEW -d '$URL'" | Out-Null
	exit 3
}

Write-Host "Done." -ForegroundColor Green
Write-Host "URL: $URL" -ForegroundColor Gray
