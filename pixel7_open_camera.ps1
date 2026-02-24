param(
    [string]$DeviceSerial = ""
)

$ErrorActionPreference = 'Stop'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ('adb.exe が見つかりません: {0}' -f $adbExe) -ForegroundColor Red
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

Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Cyan

function Invoke-AmStart([string]$action) {
    $out = (& $adbExe -s $DeviceSerial shell "am start -a $action" 2>&1 | Out-String).Trim()
    if ($out) { $out | Out-Host }
    return ($out -notmatch 'Error: Activity not started')
}

Write-Host 'Opening camera...' -ForegroundColor Cyan

# 端末/構成で解決できるものを順に試す
$actions = @(
    'android.media.action.STILL_IMAGE_CAMERA',
    'android.media.action.STILL_IMAGE_CAMERA_SECURE',
    'android.media.action.VIDEO_CAMERA',
    'android.media.action.IMAGE_CAPTURE'
)

$opened = $false
foreach ($a in $actions) {
    if (Invoke-AmStart $a) {
        $opened = $true
        break
    }
}

if (-not $opened) {
    # 最終手段: Google Camera（Pixel標準）を直接起動
    $pkg = 'com.google.android.GoogleCamera'
    Write-Host ('Fallback: monkey launch {0}' -f $pkg) -ForegroundColor Yellow
    $out = (& $adbExe -s $DeviceSerial shell "monkey -p $pkg -c android.intent.category.LAUNCHER 1" 2>&1 | Out-String).Trim()
    if ($out) { $out | Out-Host }
    if ($out -match 'Events injected: 1') { $opened = $true }
}

if (-not $opened) {
    # 最終フォールバック: カメラキーイベント
    Write-Host 'Fallback: KEYCODE_CAMERA (27)' -ForegroundColor Yellow
    try {
        & $adbExe -s $DeviceSerial shell 'input keyevent 27' | Out-Null
        Start-Sleep -Milliseconds 500
        $opened = $true
    } catch {
        $opened = $false
    }
}

if ($opened) {
    Write-Host 'Camera opened.' -ForegroundColor Green
    exit 0
}

Write-Host 'Camera could not be opened (will continue anyway).' -ForegroundColor Yellow
exit 1

