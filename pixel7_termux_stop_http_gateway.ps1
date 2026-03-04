param(
    [string]$DeviceSerial = "",
    [int]$EnterCount = 1,
    [int]$WaitStopSec = 20,
    [int]$ApiPort = 5122
)

$ErrorActionPreference = 'Stop'

if ($EnterCount -lt 1) { $EnterCount = 1 }
if ($EnterCount -gt 3) { $EnterCount = 3 }
if ($WaitStopSec -lt 0) { $WaitStopSec = 0 }
if ($WaitStopSec -gt 600) { $WaitStopSec = 600 }
if ($ApiPort -lt 1 -or $ApiPort -gt 65535) { throw "ApiPort must be 1..65535 (got: $ApiPort)" }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe not found: {0}" -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-DevicesText {
    return (& $adbExe devices | Out-String)
}

function Invoke-AdbShellBestEffort([string]$cmd) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $adbExe
    $psi.Arguments = ("-s {0} shell {1}" -f $DeviceSerial, $cmd)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    if ($p) {
        try {
            $null = $p.StandardOutput.ReadToEnd()
            $null = $p.StandardError.ReadToEnd()
            $p.WaitForExit()
        } catch {}
    }
}

function Get-DefaultSerial {
    $txt = Get-DevicesText

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

    return ""
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'Device not found. Considered already stopped.' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 0
}

Write-Host '=== Pixel7 Termux Stop HTTP Gateway (ADB assisted) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Port  : {0}" -f $ApiPort) -ForegroundColor Gray

# Bring Termux to front
$pkg = 'com.termux'
Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
Start-Sleep -Milliseconds 600

# Best-effort stop (Termux shell)
function Send-TermuxLine([string]$line) {
    $encoded = ($line -replace ' ', '%s')
    if ($encoded -match "'") {
        throw "Send-TermuxLine: single-quote is not supported in payload: $line"
    }
    Write-Host ("Typing: {0}" -f $line) -ForegroundColor DarkGray
    & $adbExe -s $DeviceSerial shell "input text '$encoded'" | Out-Null
    Start-Sleep -Milliseconds 120
    & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_ENTER' | Out-Null
    Start-Sleep -Milliseconds 200
}

function Test-Listening {
    $needle = (":{0}\s" -f [regex]::Escape([string]$ApiPort))

    $out = (& $adbExe -s $DeviceSerial shell 'ss -ltn 2>/dev/null' 2>$null | Out-String)
    if ($out -match $needle) { return $true }

    $out2 = (& $adbExe -s $DeviceSerial shell 'netstat -ltn 2>/dev/null' 2>$null | Out-String)
    return ($out2 -match $needle)
}

function Wait-ForStop {
    if ($WaitStopSec -le 0) { return (-not (Test-Listening)) }
    $deadline = (Get-Date).AddSeconds($WaitStopSec)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-Listening)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return (-not (Test-Listening))
}

Send-TermuxLine "pkill -f pixel7_api_gateway.py"

if (Wait-ForStop) {
    Write-Host 'OK (port is stopped)' -ForegroundColor Green
    exit 0
}

Write-Host 'NG: gateway still appears to be listening' -ForegroundColor Yellow
exit 2
