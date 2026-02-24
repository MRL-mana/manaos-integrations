param(
    [string]$DeviceSerial = "",
    [string]$DestDir = "/sdcard/Download/manaos_pixel7_http",
    [int]$EnterCount = 1
)

$ErrorActionPreference = 'Stop'

if ($EnterCount -lt 1) { $EnterCount = 1 }
if ($EnterCount -gt 3) { $EnterCount = 3 }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe が見つかりません: {0}" -f $adbExe) -ForegroundColor Red
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

# Bring Termux to front
$pkg = 'com.termux'
& $adbExe -s $DeviceSerial shell "monkey -p $pkg -c android.intent.category.LAUNCHER 1" | Out-Null
Start-Sleep -Milliseconds 600

function Send-TermuxLine([string]$line) {
    # adb input text: spaces must be encoded as %s
    $encoded = ($line -replace ' ', '%s')
    # Quote-safe for `adb shell` (prefer double-quotes so single-quotes in the payload don't break)
    $encoded = ($encoded -replace '"', '\"')
    Write-Host ("Typing: {0}" -f $line) -ForegroundColor DarkGray
    & $adbExe -s $DeviceSerial shell "input text \"$encoded\"" | Out-Null
    Start-Sleep -Milliseconds 120
    & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_ENTER' | Out-Null
    Start-Sleep -Milliseconds 200
}

Send-TermuxLine ("cd {0}" -f $DestDir)
Send-TermuxLine 'chmod +x start_pixel7_api_gateway.sh'
Send-TermuxLine './start_pixel7_api_gateway.sh'

Write-Host 'OK (check Pixel Termux screen/log)' -ForegroundColor Green
