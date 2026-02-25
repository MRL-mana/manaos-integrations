param(
    [string]$DeviceSerial = "",
    [string]$TailscaleTarget = "100.84.2.125:5555",
    [int]$BootWaitSec = 35,
    [int]$HealthWaitSec = 360,
    [int]$SmokeTimeoutSec = 8
)

$ErrorActionPreference = 'Stop'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe が見つかりません: {0}" -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-DevicesText {
    return (& $adbExe devices -l 2>&1 | Out-String)
}

function Get-OnlineSerialFromDevicesText([string]$txt, [string]$preferredSerial) {
    if (-not $txt) { return '' }

    # Prefer explicitly provided serial if it is online
    if ($preferredSerial -and ($txt -match ([regex]::Escape($preferredSerial) + '\s+device\b'))) {
        return $preferredSerial
    }

    # Prefer any USB device
    $usbLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '\sdevice\b' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
        } | Select-Object -First 1)
    if ($usbLine) {
        return (($usbLine -split '\s+')[0])
    }

    # Then wifi :5555 device
    $wifiLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '^[0-9.]+:5555\s+device\b'
        } | Select-Object -First 1)
    if ($wifiLine) {
        return (($wifiLine -split '\s+')[0])
    }

    return ''
}

function Get-DefaultSerial {
    $txt = Get-DevicesText
    if (-not $txt) { return "" }

    if ($env:PIXEL7_ADB_SERIAL -and ($txt -match ([regex]::Escape($env:PIXEL7_ADB_SERIAL) + '\s+device'))) {
        return $env:PIXEL7_ADB_SERIAL
    }

    # Prefer USB serial if present
    $usbLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '\sdevice\b' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
        } | Select-Object -First 1)
    if ($usbLine) {
        return (($usbLine -split '\s+')[0])
    }

    # Fall back to wireless :5555 device
    $wifiLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '^[0-9.]+:5555\s+device\b'
        } | Select-Object -First 1)
    if ($wifiLine) {
        return (($wifiLine -split '\s+')[0])
    }

    return ""
}

if ($BootWaitSec -lt 5) { $BootWaitSec = 5 }
if ($BootWaitSec -gt 240) { $BootWaitSec = 240 }
if ($HealthWaitSec -lt 30) { $HealthWaitSec = 30 }
if ($HealthWaitSec -gt 900) { $HealthWaitSec = 900 }
if ($SmokeTimeoutSec -lt 3) { $SmokeTimeoutSec = 3 }
if ($SmokeTimeoutSec -gt 30) { $SmokeTimeoutSec = 30 }

Write-Host '=== Pixel7 HTTP Autostart Reboot Test ===' -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    # best-effort: try reconnect wireless
    try { $null = (& $adbExe connect $TailscaleTarget 2>&1 | Out-String) } catch {}
    Start-Sleep -Seconds 1
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。先にUSB接続 or 無線ADB接続を確認してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray

$bootLog = '/storage/emulated/0/Download/pixel7_termux_boot.log'
Write-Host '[pre] boot log tail' -ForegroundColor Gray
try {
    & $adbExe -s $DeviceSerial shell "tail -n 20 $bootLog 2>/dev/null | head -n 20 || echo NO_BOOT_LOG" | Out-Host
} catch {
    Write-Host 'WARN: cannot read boot log (non-fatal)' -ForegroundColor DarkGray
}

Write-Host '[action] reboot' -ForegroundColor Yellow
& $adbExe -s $DeviceSerial reboot | Out-Null

Write-Host '[wait] device online' -ForegroundColor Gray
$deadline = (Get-Date).AddMinutes(7)
$onlineSerial = ""
while ((Get-Date) -lt $deadline) {
    try { $null = (& $adbExe connect $TailscaleTarget 2>&1 | Out-String) } catch {}
    $txt = Get-DevicesText
    $preferred = ''
    if ($env:PIXEL7_ADB_SERIAL) { $preferred = $env:PIXEL7_ADB_SERIAL }
    if (-not $preferred) { $preferred = $DeviceSerial }
    $onlineSerial = Get-OnlineSerialFromDevicesText $txt $preferred
    if ($onlineSerial) { break }
    Start-Sleep -Seconds 6
}

if (-not $onlineSerial) {
    Write-Host 'TIMEOUT: device did not come back online' -ForegroundColor Red
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 4
}

Write-Host ("OK: online serial={0}" -f $onlineSerial) -ForegroundColor Green

Write-Host ("[wait] Termux:Boot ({0}s)" -f $BootWaitSec) -ForegroundColor Gray
Start-Sleep -Seconds $BootWaitSec

Write-Host '[post] boot log tail' -ForegroundColor Gray
try {
    & $adbExe -s $onlineSerial shell "tail -n 40 $bootLog 2>/dev/null | head -n 40 || echo NO_BOOT_LOG" | Out-Host
} catch {
    Write-Host 'WARN: cannot read boot log (non-fatal)' -ForegroundColor DarkGray
}

Write-Host '[setup] adb forward 5122' -ForegroundColor Gray
try { & $adbExe -s $onlineSerial forward --remove tcp:5122 2>$null | Out-Null } catch {}
try { & $adbExe -s $onlineSerial forward tcp:5122 tcp:5122 2>$null | Out-Null } catch {}

Write-Host ("[wait] /health up to {0}s" -f $HealthWaitSec) -ForegroundColor Gray
$hDeadline = (Get-Date).AddSeconds($HealthWaitSec)
$healthy = $false
$lastErr = ''
while ((Get-Date) -lt $hDeadline) {
    try {
        $h = Invoke-RestMethod -Uri 'http://127.0.0.1:5122/health' -TimeoutSec 4
        if ($h.status -eq 'healthy') {
            $healthy = $true
            break
        }
        $lastErr = 'not_healthy_response'
    } catch {
        $lastErr = $_.Exception.Message
    }
    Start-Sleep -Seconds 10
}

if (-not $healthy) {
    Write-Host 'NG: /health not ready' -ForegroundColor Red
    Write-Host ("last_error={0}" -f $lastErr) -ForegroundColor Yellow
    Write-Host 'NOTE: 端末がロック中だとTermux:Bootが遅れる/動かない場合があります。Pixelのロック解除を一度してから再実行してください。' -ForegroundColor Yellow
    exit 5
}

Write-Host 'OK: /health healthy' -ForegroundColor Green

Write-Host '[run] smoketest' -ForegroundColor Cyan
$smoke = Join-Path $PSScriptRoot 'pixel7_http_smoketest.ps1'
& pwsh -NoProfile -ExecutionPolicy Bypass -File $smoke -TimeoutSec $SmokeTimeoutSec
exit $LASTEXITCODE
