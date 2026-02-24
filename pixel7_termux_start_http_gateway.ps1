param(
    [string]$DeviceSerial = "",
    [string]$DestDir = '$HOME',
    [int]$EnterCount = 1,
    [string]$LogPath = "",
    [int]$WaitListenSec = 120,
    [int]$ApiPort = 5122
)

$ErrorActionPreference = 'Stop'

if ($EnterCount -lt 1) { $EnterCount = 1 }
if ($EnterCount -gt 3) { $EnterCount = 3 }
if ($WaitListenSec -lt 0) { $WaitListenSec = 0 }
if ($WaitListenSec -gt 600) { $WaitListenSec = 600 }
if ($ApiPort -lt 1 -or $ApiPort -gt 65535) { throw "ApiPort must be 1..65535 (got: $ApiPort)" }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe が見つかりません: {0}" -f $adbExe) -ForegroundColor Red
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
    Write-Host 'デバイスが見つかりません。先に「Pixel7 無線ADB復旧（5555）」を実行してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host '=== Pixel7 Termux Start HTTP Gateway (ADB assisted) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Dest  : {0}" -f $DestDir) -ForegroundColor Gray
Write-Host ("Port  : {0}" -f $ApiPort) -ForegroundColor Gray

function Resolve-LogPath([string]$p) {
    $p = [string]($p ?? '')
    if ([string]::IsNullOrWhiteSpace($p)) { return '' }

    # /sdcard is a symlink; on some devices/shell contexts it can be missing/broken.
    # Prefer /storage/emulated/0 for external storage.
    if ($p -like '/sdcard/*') {
        return ('/storage/emulated/0' + $p.Substring('/sdcard'.Length))
    }
    if ($p -like '/storage/self/primary/*') {
        return ('/storage/emulated/0' + $p.Substring('/storage/self/primary'.Length))
    }
    return $p
}

$LogPathResolved = Resolve-LogPath $LogPath
if ($LogPathResolved -and $LogPathResolved -ne $LogPath) {
    Write-Host ("LogPath corrected: {0} -> {1}" -f $LogPath, $LogPathResolved) -ForegroundColor DarkGray
}

# Bring Termux to front
$pkg = 'com.termux'
Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
Start-Sleep -Milliseconds 600

function Send-TermuxLine([string]$line) {
    # adb input text: spaces must be encoded as %s
    $encoded = ($line -replace ' ', '%s')
    if ($encoded -match "'") {
        throw "Send-TermuxLine: single-quote is not supported in payload: $line"
    }
    Write-Host ("Typing: {0}" -f $line) -ForegroundColor DarkGray
    # Use single-quotes so that metacharacters like >, &, | are not interpreted by /system/bin/sh
    & $adbExe -s $DeviceSerial shell "input text '$encoded'" | Out-Null
    Start-Sleep -Milliseconds 120
    & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_ENTER' | Out-Null
    Start-Sleep -Milliseconds 200
}

function Test-Listening {
    # Avoid requiring Termux storage permissions; inspect sockets from adb shell.
    $cmd = "(ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep ':{0} ' || true" -f $ApiPort
    $out = (& $adbExe -s $DeviceSerial shell $cmd 2>$null | Out-String)
    return ($out -match (":{0}\s" -f [regex]::Escape([string]$ApiPort)))
}

function Wait-ForListen {
    if ($WaitListenSec -le 0) { return (Test-Listening) }
    $deadline = (Get-Date).AddSeconds($WaitListenSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Listening) { return $true }
        Start-Sleep -Milliseconds 600
    }
    return $false
}

Send-TermuxLine ("cd {0}" -f $DestDir)
Send-TermuxLine 'chmod +x start_pixel7_api_gateway.sh'
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    # /sdcard is often mounted with noexec; run via bash explicitly
    Send-TermuxLine 'bash ./start_pixel7_api_gateway.sh'
} else {
    # Run in background and log to an adb-accessible location
    # NOTE: do not wrap path in quotes to keep adb input simple
    $lp = $LogPathResolved
    $dir = [System.IO.Path]::GetDirectoryName($lp)
    if ($dir) {
        # Ensure directory exists (Android mkdir -p)
        Send-TermuxLine ("mkdir -p {0}" -f $dir)
    }

    # Keep the command as short as possible to avoid adb input truncation.
    Send-TermuxLine ("bash ./start_pixel7_api_gateway.sh > {0} 2>&1 &" -f $lp)
    Send-TermuxLine ("echo STARTED > {0}.started" -f $lp)
}

if (Wait-ForListen) {
    Write-Host 'OK (port is listening)' -ForegroundColor Green
    exit 0
}

Write-Host 'NG: gateway did not start listening in time' -ForegroundColor Yellow
Write-Host 'Hints:' -ForegroundColor Gray
Write-Host '- Run "ManaOS: Pixel7 HTTP Gateway 配置（Termux bootstrap）" first (ensures python/curl + files in $HOME)' -ForegroundColor Gray
Write-Host '- Ensure Termux is unlocked/in foreground and no permission prompts are blocking' -ForegroundColor Gray
Write-Host '- If you set LogPath under /sdcard, run termux-setup-storage in Termux once' -ForegroundColor Gray
exit 2
