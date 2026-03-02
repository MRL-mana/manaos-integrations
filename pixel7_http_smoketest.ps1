param(
    [int]$TimeoutSec = 5,
    [switch]$TryOpenOpenWebUI,
    [switch]$SkipFallbackActions,
    [bool]$AutoRecoverAdb = $true
)

$ErrorActionPreference = 'Stop'

$httpCtl = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$autoCtl = Join-Path $PSScriptRoot 'pixel7_control_auto.ps1'
$profileCheck = Join-Path $PSScriptRoot 'pixel7_check_api_profile.ps1'
$adbRecover = Join-Path $PSScriptRoot 'pixel7_adb_recover_wireless.ps1'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }

Write-Host '=== Pixel7 HTTP Smoke Test ===' -ForegroundColor Cyan

$useLocal = $false
$allOk = $true

function Get-RemoteBaseUrl {
    if ($env:PIXEL7_API_BASE) {
        return $env:PIXEL7_API_BASE.TrimEnd('/')
    }

    $apiHost = if ($env:PIXEL7_API_HOST) {
        $env:PIXEL7_API_HOST
    } elseif ($env:PIXEL7_TAILSCALE_IP) {
        $env:PIXEL7_TAILSCALE_IP
    } elseif ($env:PIXEL7_IP) {
        $env:PIXEL7_IP
    } else {
        '100.84.2.125'
    }

    $port = if ($env:PIXEL7_API_PORT) { $env:PIXEL7_API_PORT } else { '5122' }
    return ("http://{0}:{1}" -f $apiHost, $port)
}

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

Write-Host '\n[1b] api profile (/)' -ForegroundColor Gray
if (Test-Path $profileCheck) {
    try {
        if ($useLocal) {
            & $profileCheck -Require any -BaseUrl 'http://127.0.0.1:5122' -TimeoutSec $TimeoutSec | Out-Host
        } else {
            & $profileCheck -Require any -BaseUrl (Get-RemoteBaseUrl) -TimeoutSec $TimeoutSec | Out-Host
        }
    } catch {
        Write-Host ("WARN: profile check failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
} else {
    Write-Host 'SKIP: pixel7_check_api_profile.ps1 not found' -ForegroundColor Yellow
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

if ($SkipFallbackActions) {
    Write-Host '\n[3] fallback actions' -ForegroundColor Gray
    Write-Host 'SKIP: fallback actions disabled by -SkipFallbackActions' -ForegroundColor Yellow
} else {
    if ($AutoRecoverAdb -and (Test-Path $adbRecover)) {
        $serialBefore = Get-DefaultSerial
        if ([string]::IsNullOrWhiteSpace($serialBefore)) {
            Write-Host '\n[2c] adb recovery (one-shot)' -ForegroundColor Gray
            try {
                & $adbRecover -RestartAdb -RemoteOnly | Out-Host
            } catch {
                Write-Host ("WARN: adb recover failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
            }
        }
    }

    Write-Host '\n[3] HTTP→ADB fallback action (OpenHttpShortcuts)' -ForegroundColor Gray
    if (Test-Path $autoCtl) {
        try {
            & $autoCtl -Action OpenHttpShortcuts -Mode HTTPFirst -TimeoutSec $TimeoutSec | Out-Host
            if ($LASTEXITCODE -ne 0) {
                Write-Host ("NG: fallback action exit code: {0}" -f $LASTEXITCODE) -ForegroundColor Red
                $allOk = $false
            }
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
                if ($LASTEXITCODE -ne 0) {
                    Write-Host ("NG: OpenOpenWebUI exit code: {0}" -f $LASTEXITCODE) -ForegroundColor Red
                    $allOk = $false
                }
            } catch {
                Write-Host ("NG: OpenOpenWebUI failed: {0}" -f $_.Exception.Message) -ForegroundColor Red
                $allOk = $false
            }
        }
    }
}

if ($allOk) {
    Write-Host '\nOK' -ForegroundColor Green
    exit 0
}

Write-Host '\nNG' -ForegroundColor Yellow
exit 2
