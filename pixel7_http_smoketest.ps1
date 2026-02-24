param(
    [int]$TimeoutSec = 5,
    [switch]$TryOpenOpenWebUI
)

$ErrorActionPreference = 'Stop'

$httpCtl = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$autoCtl = Join-Path $PSScriptRoot 'pixel7_control_auto.ps1'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }

Write-Host '=== Pixel7 HTTP Smoke Test ===' -ForegroundColor Cyan

$useLocal = $false
$allOk = $true

function Get-DevicesText {
    if (-not (Test-Path $adbExe)) { return '' }
    return (& $adbExe devices | Out-String)
}

function Get-DefaultSerial {
    $txt = Get-DevicesText
    if (-not $txt) { return '' }

    if ($env:PIXEL7_ADB_SERIAL -and ($txt -match ([regex]::Escape($env:PIXEL7_ADB_SERIAL) + '\s+device'))) {
        return $env:PIXEL7_ADB_SERIAL
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

    return ''
}

if (Test-Path $adbExe) {
    try {
        $serial = Get-DefaultSerial
        # Best-effort: set adb forward so localhost can be used even without Tailscale
        if ($serial) {
            & $adbExe -s $serial forward --remove tcp:5122 2>$null | Out-Null
            & $adbExe -s $serial forward tcp:5122 tcp:5122 2>$null | Out-Null
        } else {
            & $adbExe forward --remove tcp:5122 2>$null | Out-Null
            & $adbExe forward tcp:5122 tcp:5122 2>$null | Out-Null
        }
    } catch {}
}

Write-Host '\n[1] health (/health)' -ForegroundColor Gray
$healthOk = $false
try {
    & $httpCtl -Action Health -PixelHost 127.0.0.1 -Port 5122 -TimeoutSec $TimeoutSec | Out-Host
    $useLocal = $true
    $healthOk = $true
} catch {
    Write-Host ("NG(localhost): health failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    try {
        & $httpCtl -Action Health -TimeoutSec $TimeoutSec | Out-Host
        $healthOk = $true
    } catch {
        Write-Host ("NG: health failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
        $healthOk = $false
    }
}

if (-not $healthOk) {
    $allOk = $false
}

Write-Host '\n[2] status (/api/status) requires PIXEL7_API_TOKEN' -ForegroundColor Gray
$tokenFile = Join-Path $PSScriptRoot '.pixel7_api_token.txt'
if (-not $env:PIXEL7_API_TOKEN -and -not (Test-Path $tokenFile)) {
    Write-Host 'SKIP: PIXEL7_API_TOKEN not set (and token file not found)' -ForegroundColor Yellow
} else {
    try {
        if ($useLocal) {
            & $httpCtl -Action Status -PixelHost 127.0.0.1 -Port 5122 -TimeoutSec $TimeoutSec | Out-Host
        } else {
            & $httpCtl -Action Status -TimeoutSec $TimeoutSec | Out-Host
        }
    } catch {
        Write-Host ("NG: status failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
        $allOk = $false
    }

    Write-Host '\n[2b] macro commands (/api/macro/commands)' -ForegroundColor Gray
    try {
        if ($useLocal) {
            & $httpCtl -Action MacroCommands -PixelHost 127.0.0.1 -Port 5122 -TimeoutSec $TimeoutSec | Out-Host
        } else {
            & $httpCtl -Action MacroCommands -TimeoutSec $TimeoutSec | Out-Host
        }
    } catch {
        Write-Host ("NG: macro commands failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host '\n[3] HTTP→ADB fallback action (OpenHttpShortcuts)' -ForegroundColor Gray
if (Test-Path $autoCtl) {
    try {
        & $autoCtl -Action OpenHttpShortcuts -Mode HTTPFirst -TimeoutSec $TimeoutSec | Out-Host
    } catch {
        Write-Host ("NG: fallback action failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
        $allOk = $false
    }
} else {
    Write-Host 'SKIP: pixel7_control_auto.ps1 not found' -ForegroundColor Yellow
}

if ($TryOpenOpenWebUI) {
    Write-Host '\n[4] HTTP→ADB fallback action (OpenOpenWebUI)' -ForegroundColor Gray
    if (Test-Path $autoCtl) {
        try {
            & $autoCtl -Action OpenOpenWebUI -Mode HTTPFirst -TimeoutSec $TimeoutSec | Out-Host
        } catch {
            Write-Host ("NG: OpenOpenWebUI failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
            $allOk = $false
        }
    }
}

if ($allOk) {
    Write-Host '\nOK' -ForegroundColor Green
    exit 0
}

Write-Host '\nNG' -ForegroundColor Yellow
exit 2
