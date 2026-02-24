param(
    [string]$PixelTailscaleIp = "",
    [string]$AdbPort = "5555",
    [string]$WifiIp = "",
    [string]$UsbSerial = "",
    [switch]$RestartAdb,
    [switch]$RemoteOnly
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($PixelTailscaleIp)) {
    # Prefer MagicDNS hostname if available (easier when IP changes)
    if ($env:PIXEL7_TAILSCALE_HOST) {
        $PixelTailscaleIp = $env:PIXEL7_TAILSCALE_HOST
    } else {
        $PixelTailscaleIp = if ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } else { '100.84.2.125' }
    }
}
if ([string]::IsNullOrWhiteSpace($UsbSerial)) {
    $UsbSerial = if ($env:PIXEL7_USB_SERIAL) { $env:PIXEL7_USB_SERIAL } else { '39111JEHN00394' }
}

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe not found: {0}" -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-DevicesText {
    return (& $adbExe devices | Out-String)
}

function Get-UsbConnectedDevice {
    $raw = Get-DevicesText
    $line = ($raw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
        } | Select-Object -First 1)
    if (-not $line) { return "" }
    return ($line -replace '\s+device$','')
}

function Test-DeviceOnline([string]$serial) {
    $txt = Get-DevicesText
    $pat = [regex]::Escape($serial) + '\s+device'
    return ($txt -match $pat)
}

function Connect([string]$target) {
    Write-Host ('adb connect {0} ...' -f $target) -ForegroundColor Cyan
    $out = (& $adbExe connect $target 2>&1 | Out-String).Trim()
    if ($out) { $out | Out-Host }
    Start-Sleep -Milliseconds 600
    return (Test-DeviceOnline $target)
}

function Get-WifiIpViaUsb([string]$usbSerial) {
    try {
        $line = (& $adbExe -s $usbSerial shell "ip -f inet addr show wlan0 | grep -E 'inet ' || true" | Out-String).Trim()
        if ($line -match 'inet\s+([0-9.]+)/') {
            return $Matches[1]
        }
    } catch {
        return ""
    }
    return ""
}

Write-Host '=== Pixel7 Wireless ADB Recover (5555) ===' -ForegroundColor Cyan

if ($RestartAdb) {
    & $adbExe kill-server | Out-Null
    & $adbExe start-server | Out-Null
}

Write-Host (Get-DevicesText) -ForegroundColor Gray

# Prepare Wi-Fi IP (optional; skipped in RemoteOnly)
if (-not $RemoteOnly) {
    if ([string]::IsNullOrWhiteSpace($WifiIp)) {
        $usbNow = Get-UsbConnectedDevice
        if ($usbNow) {
            $WifiIp = Get-WifiIpViaUsb $usbNow
        } elseif (-not [string]::IsNullOrWhiteSpace($UsbSerial) -and (Test-DeviceOnline $UsbSerial)) {
            $WifiIp = Get-WifiIpViaUsb $UsbSerial
        }
    }
}

$portCandidates = @('5555')
if (-not [string]::IsNullOrWhiteSpace($AdbPort) -and $AdbPort -ne '5555') { $portCandidates += $AdbPort }
if ($env:PIXEL7_ADB_PORT -and ($env:PIXEL7_ADB_PORT -ne '5555') -and ($env:PIXEL7_ADB_PORT -ne $AdbPort)) { $portCandidates += $env:PIXEL7_ADB_PORT }
$portCandidates = $portCandidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

$targets = @()
foreach ($p in $portCandidates) {
    $targets += ('{0}:{1}' -f $PixelTailscaleIp, $p)
    if (-not $RemoteOnly) {
        if (-not [string]::IsNullOrWhiteSpace($WifiIp)) {
            $targets += ('{0}:{1}' -f $WifiIp, $p)
        }
    }
}
$targets = $targets | Select-Object -Unique

foreach ($t in $targets) {
    if (Test-DeviceOnline $t) {
        Write-Host ('OK: already online {0}' -f $t) -ForegroundColor Green
        exit 0
    }
}

$connected = $false
foreach ($t in $targets) {
    if (Connect $t) { $connected = $true; break }
}

if ($connected) {
    Write-Host 'Wireless ADB recovered.' -ForegroundColor Green
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 0
}

if ($RemoteOnly) {
    Write-Host 'RemoteOnly: skip USB tcpip re-enable.' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

# USB縺後≠繧後・ tcpip 5555 繧貞・譛牙柑蛹悶＠縺ｦ蜀崎ｩｦ陦・
$usb = Get-UsbConnectedDevice
if (-not $usb) {
    if (-not [string]::IsNullOrWhiteSpace($UsbSerial) -and (Test-DeviceOnline $UsbSerial)) {
        $usb = $UsbSerial
    }
}

if ($usb) {
    Write-Host ("Enable tcpip {0} via USB: {1}" -f $AdbPort, $usb) -ForegroundColor Yellow
    (& $adbExe -s $usb tcpip $AdbPort 2>&1 | Out-String).Trim() | Out-Host
    Start-Sleep -Seconds 2

    foreach ($t in $targets) {
        if (Connect $t) {
            Write-Host 'Wireless ADB recovered.' -ForegroundColor Green
            Write-Host (Get-DevicesText) -ForegroundColor Gray
            exit 0
        }
    }
}

Write-Host 'Failed to recover wireless ADB. Check Pixel: Tailscale / Wi-Fi / Wireless debugging.' -ForegroundColor Yellow
Write-Host (Get-DevicesText) -ForegroundColor Gray
exit 2

