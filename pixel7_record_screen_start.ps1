param(
    [string]$DeviceSerial = "",
    [string]$OutDir = "",
    [string]$RemotePath = "",
    [switch]$StopExisting
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

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $env:USERPROFILE 'Desktop\screenrecordings'
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
if ([string]::IsNullOrWhiteSpace($RemotePath)) {
    $RemotePath = "/data/local/tmp/pixel7_record_manual_${ts}.mp4"
}

$statePath = Join-Path $PSScriptRoot '.pixel7_screenrecord_state.json'
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$adbLog = Join-Path $logDir ("pixel7_screenrecord_start_${ts}.log")

if ($StopExisting) {
    try {
        & $adbExe -s $DeviceSerial shell 'pkill -2 screenrecord 2>/dev/null || killall -2 screenrecord 2>/dev/null || true' | Out-Null
        Start-Sleep -Milliseconds 500
    } catch {}
}

Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Cyan
Write-Host ('Remote: {0}' -f $RemotePath) -ForegroundColor Gray
Write-Host ('OutDir:  {0}' -f $OutDir) -ForegroundColor Green

# adb shell screenrecord は停止までブロックするので、PC側は別プロセスで起動しておく
$adbParams = @('-s', $DeviceSerial, 'shell', 'screenrecord', $RemotePath)
$p = Start-Process -FilePath $adbExe -ArgumentList $adbParams -WindowStyle Hidden -RedirectStandardOutput $adbLog -RedirectStandardError 'NUL' -PassThru

$state = [ordered]@{
    deviceSerial = $DeviceSerial
    remotePath   = $RemotePath
    outDir       = $OutDir
    startedAt    = (Get-Date).ToString('o')
    adbPid       = $p.Id
}
$state | ConvertTo-Json -Depth 4 | Set-Content -Path $statePath -Encoding UTF8

Write-Host ('Recording started. (adb PID={0})' -f $p.Id) -ForegroundColor Green
Write-Host ('Stop & save: powershell -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f (Join-Path $PSScriptRoot 'pixel7_record_screen_stop.ps1')) -ForegroundColor Gray
