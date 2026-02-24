param(
    [string]$DeviceSerial = "",
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

Write-Host '=== Pixel7 Termux Stop HTTP Gateway (ADB assisted) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray

# Bring Termux to front
$pkg = 'com.termux'
& $adbExe -s $DeviceSerial shell "monkey -p $pkg -c android.intent.category.LAUNCHER 1" | Out-Null
Start-Sleep -Milliseconds 600

# Best-effort stop (Termux shell)
function Send-TermuxLine([string]$line) {
    $encoded = ($line -replace ' ', '%s')
    $encoded = ($encoded -replace '"', '\"')
    Write-Host ("Typing: {0}" -f $line) -ForegroundColor DarkGray
    & $adbExe -s $DeviceSerial shell "input text \"$encoded\"" | Out-Null
    Start-Sleep -Milliseconds 120
    & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_ENTER' | Out-Null
    Start-Sleep -Milliseconds 200
}

Send-TermuxLine "pkill -f pixel7_api_gateway.py || true"

Write-Host 'OK (check Pixel Termux screen/log)' -ForegroundColor Green
