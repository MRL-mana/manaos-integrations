Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Pixel7 Termux Bootstrap HTTP Gateway (ADB assisted)
# - Intentionally avoids a param() block to stay robust across PS 5.1 invocation edge cases.

$DeviceSerial = ''
$HostPort = 18000
$ServerBase = 'http://127.0.0.1'
$SleepMs = 250
$InstallWaitSec = $null

for ($i = 0; $i -lt $args.Count; $i++) {
    $a = [string]$args[$i]
    switch ($a) {
        '-DeviceSerial' {
            if ($i + 1 -lt $args.Count) { $DeviceSerial = [string]$args[++$i] }
        }
        '-HostPort' {
            if ($i + 1 -lt $args.Count) {
                try { $HostPort = [int]$args[++$i] } catch {}
            }
        }
        '-ServerBase' {
            if ($i + 1 -lt $args.Count) { $ServerBase = [string]$args[++$i] }
        }
        '-SleepMs' {
            if ($i + 1 -lt $args.Count) {
                try { $SleepMs = [int]$args[++$i] } catch {}
            }
        }
        '-InstallWaitSec' {
            if ($i + 1 -lt $args.Count) {
                try { $InstallWaitSec = [int]$args[++$i] } catch {}
            }
        }
        default {
        }
    }
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) { $DeviceSerial = '' }
if ($HostPort -lt 1024) { $HostPort = 18000 }
if ($HostPort -gt 65535) { $HostPort = 18000 }
if ([string]::IsNullOrWhiteSpace($ServerBase)) { $ServerBase = 'http://127.0.0.1' }
if ($SleepMs -lt 50) { $SleepMs = 50 }
if ($SleepMs -gt 2000) { $SleepMs = 2000 }
if ($null -eq $InstallWaitSec) { $InstallWaitSec = 90 }
if ($InstallWaitSec -lt 0) { $InstallWaitSec = 0 }
if ($InstallWaitSec -gt 600) { $InstallWaitSec = 600 }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe not found: {0}" -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-DevicesText {
    return (& $adbExe devices | Out-String)
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

    return ''
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

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'No adb device found. Check USB debugging or wireless ADB first.' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

$base = $ServerBase.TrimEnd('/') + ":$HostPort"

Write-Host '=== Pixel7 Termux Bootstrap HTTP Gateway (ADB assisted) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Fetch : {0}" -f $base) -ForegroundColor Gray

# Bring Termux to front
$pkg = 'com.termux'
Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
Start-Sleep -Milliseconds 600

function Send-TermuxLine([string]$line) {
    $encoded = ($line -replace ' ', '%s')
    if ($encoded -match "'") {
        throw "Send-TermuxLine: single-quote is not supported in payload: $line"
    }
    Write-Host ("Typing: {0}" -f $line) -ForegroundColor DarkGray
    & $adbExe -s $DeviceSerial shell "input text '$encoded'" | Out-Null
    Start-Sleep -Milliseconds 120
    & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_ENTER' | Out-Null
    Start-Sleep -Milliseconds $SleepMs
}

# Ensure curl/python, then fetch into $HOME
Send-TermuxLine 'cd $HOME'
Send-TermuxLine 'pkg install -y curl python'

if ($InstallWaitSec -gt 0) {
    Write-Host ("Waiting {0}s for Termux pkg install to finish..." -f $InstallWaitSec) -ForegroundColor DarkGray
    Start-Sleep -Seconds $InstallWaitSec
}

Send-TermuxLine 'rm -f pixel7_api_gateway.py start_pixel7_api_gateway.sh boot_start_pixel7_api_gateway.sh api_token.txt'
Send-TermuxLine ("curl -fsSL {0}/pixel7_api_gateway.py -o pixel7_api_gateway.py" -f $base)
Send-TermuxLine ("curl -fsSL {0}/termux/start_pixel7_api_gateway.sh -o start_pixel7_api_gateway.sh" -f $base)
Send-TermuxLine ("curl -fsSL {0}/termux/boot_start_pixel7_api_gateway.sh -o boot_start_pixel7_api_gateway.sh" -f $base)
Send-TermuxLine ("curl -fsSL {0}/.pixel7_api_token.txt -o api_token.txt" -f $base)
Send-TermuxLine 'chmod +x start_pixel7_api_gateway.sh'
Send-TermuxLine 'chmod +x boot_start_pixel7_api_gateway.sh'

Write-Host 'OK (files fetched into Termux $HOME; now run start script)' -ForegroundColor Green
Write-Host 'Next: run the VS Code task to start the gateway, or execute ./start_pixel7_api_gateway.sh in Termux.' -ForegroundColor Yellow
