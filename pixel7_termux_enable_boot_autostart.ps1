param(
    [string]$DeviceSerial = "",
    [int]$SleepMs = 300,
    [switch]$OpenInstallPageIfMissing
)

$ErrorActionPreference = 'Stop'

if ($SleepMs -lt 50) { $SleepMs = 50 }
if ($SleepMs -gt 2000) { $SleepMs = 2000 }

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

function Invoke-AdbShell([string]$cmd) {
    return (& $adbExe -s $DeviceSerial shell $cmd 2>&1 | Out-String)
}

function Invoke-AdbShellBestEffort([string]$cmd) {
    try { $null = (& $adbExe -s $DeviceSerial shell $cmd 2>$null | Out-Null) } catch {}
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。先にADB接続（USB/無線）を確認してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host '=== Pixel7 Termux:Boot Autostart Setup ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray

$termuxBootPkg = 'com.termux.boot'
$installUrl = 'https://f-droid.org/packages/com.termux.boot/'

Write-Host '[check] Termux:Boot installed?' -ForegroundColor Gray
$pkgs = Invoke-AdbShell 'pm list packages com.termux.boot'
$hasBoot = ($pkgs -match 'package:com\.termux\.boot')
if (-not $hasBoot) {
    Write-Host 'Termux:Boot が未インストールです。' -ForegroundColor Yellow
    if ($OpenInstallPageIfMissing) {
        Write-Host ("[open] {0}" -f $installUrl) -ForegroundColor Gray
        Invoke-AdbShellBestEffort "am start -a android.intent.action.VIEW -d $installUrl"
        Start-Sleep -Milliseconds 400
    }
    Write-Host 'Pixelで Termux:Boot をインストール後、もう一度このスクリプトを実行してください。' -ForegroundColor Yellow
    exit 3
}

Write-Host '[setup] Whitelist Termux:Boot from device idle (best-effort)' -ForegroundColor Gray
Invoke-AdbShellBestEffort "dumpsys deviceidle whitelist +$termuxBootPkg"

# Bring Termux to front (we will configure ~/.termux/boot/...)
$termuxPkg = 'com.termux'
Invoke-AdbShellBestEffort "monkey -p $termuxPkg -c android.intent.category.LAUNCHER 1"
Start-Sleep -Milliseconds 700

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

Write-Host '[setup] Configure ~/.termux/boot/boot_start_pixel7_api_gateway.sh' -ForegroundColor Gray
Send-TermuxLine 'test -f $HOME/boot_start_pixel7_api_gateway.sh && echo HAVE_BOOT_SCRIPT || echo MISSING_BOOT_SCRIPT'
Send-TermuxLine 'mkdir -p ~/.termux/boot'
Send-TermuxLine 'cp -f $HOME/boot_start_pixel7_api_gateway.sh ~/.termux/boot/boot_start_pixel7_api_gateway.sh'
Send-TermuxLine 'chmod +x ~/.termux/boot/boot_start_pixel7_api_gateway.sh'
Send-TermuxLine 'ls -l ~/.termux/boot/boot_start_pixel7_api_gateway.sh || true'

Write-Host 'OK (autostart script configured). 再起動後に自動でHTTP Gatewayが起動します。' -ForegroundColor Green
