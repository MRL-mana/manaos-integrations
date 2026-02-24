param(
    [int]$Seconds = 30,
    [string]$DeviceSerial = "",
    [string]$OutDir = "",
    [switch]$OpenFolder,
    [switch]$KeepOnDevice
)

$ErrorActionPreference = 'Stop'

if ($Seconds -lt 1) { $Seconds = 1 }
if ($Seconds -gt 180) {
    Write-Host 'Seconds は 1〜180 の範囲にしてください（端末側制限対策）。' -ForegroundColor Yellow
    exit 2
}

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
    exit 3
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $env:USERPROFILE 'Desktop\screenrecordings'
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$remote = "/data/local/tmp/pixel7_record_${ts}.mp4"
$local = Join-Path $OutDir ("pixel7_record_{0}_{1}s.mp4" -f $ts, $Seconds)

Write-Host ('Target:  {0}' -f $DeviceSerial) -ForegroundColor Cyan
Write-Host ('Seconds: {0}' -f $Seconds) -ForegroundColor Cyan
Write-Host ('Remote:  {0}' -f $remote) -ForegroundColor Gray
Write-Host ('Local:   {0}' -f $local) -ForegroundColor Green

Write-Host 'Recording...' -ForegroundColor Cyan
& $adbExe -s $DeviceSerial shell "screenrecord --time-limit $Seconds $remote" | Out-Null

Write-Host 'Pulling...' -ForegroundColor Cyan
& $adbExe -s $DeviceSerial pull "$remote" "$local" | Out-Null

if (-not (Test-Path $local)) {
    Write-Host '録画ファイルの取得に失敗しました。' -ForegroundColor Yellow
    exit 4
}

if (-not $KeepOnDevice) {
    try { & $adbExe -s $DeviceSerial shell "rm -f $remote" | Out-Null } catch {}
}

if ($OpenFolder) {
    Start-Process -FilePath explorer.exe -ArgumentList @('/select,', $local)
}

Write-Host 'OK' -ForegroundColor Green
