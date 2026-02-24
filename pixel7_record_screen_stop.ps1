param(
    [string]$DeviceSerial = "",
    [string]$OutDir = "",
    [switch]$OpenFolder,
    [switch]$KeepOnDevice
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

$statePath = Join-Path $PSScriptRoot '.pixel7_screenrecord_state.json'
$state = $null
if (Test-Path $statePath) {
    try { $state = Get-Content $statePath -Raw | ConvertFrom-Json } catch { $state = $null }
}

$remote = $null
$adbPid = $null

if ($state) {
    if ([string]::IsNullOrWhiteSpace($DeviceSerial)) { $DeviceSerial = $state.deviceSerial }
    if ([string]::IsNullOrWhiteSpace($OutDir)) { $OutDir = $state.outDir }
    $remote = $state.remotePath
    $adbPid = $state.adbPid
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが不明です（stateも無し）。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $env:USERPROFILE 'Desktop\screenrecordings'
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Cyan

Write-Host 'Stopping screenrecord...' -ForegroundColor Cyan
& $adbExe -s $DeviceSerial shell 'pkill -2 screenrecord 2>/dev/null || killall -2 screenrecord 2>/dev/null || true' | Out-Null

# adb側プロセスが残っていれば少し待つ（なくてもOK）
if ($adbPid) {
    for ($i = 0; $i -lt 10; $i++) {
        $p = Get-Process -Id $adbPid -ErrorAction SilentlyContinue
        if (-not $p) { break }
        Start-Sleep -Milliseconds 300
    }
}

# remotePath が不明なら最新の録画ファイルを探す
if ([string]::IsNullOrWhiteSpace($remote)) {
    try {
        $remote = (& $adbExe -s $DeviceSerial shell "ls -t /data/local/tmp/pixel7_record_*.mp4 2>/dev/null | head -n 1" | Out-String).Trim()
    } catch {
        $remote = ""
    }
}

if ([string]::IsNullOrWhiteSpace($remote)) {
    Write-Host '端末側の録画ファイルが見つかりません。' -ForegroundColor Yellow
    exit 3
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$local = Join-Path $OutDir ("pixel7_record_manual_stop_{0}.mp4" -f $ts)

Write-Host ('Remote: {0}' -f $remote) -ForegroundColor Gray
Write-Host ('Local:  {0}' -f $local) -ForegroundColor Green

Write-Host 'Pulling...' -ForegroundColor Cyan
& $adbExe -s $DeviceSerial pull "$remote" "$local" | Out-Null

if (-not (Test-Path $local)) {
    Write-Host '録画ファイルの取得に失敗しました。' -ForegroundColor Yellow
    exit 4
}

if (-not $KeepOnDevice) {
    try { & $adbExe -s $DeviceSerial shell "rm -f $remote" | Out-Null } catch {}
}

# state を消す
try { Remove-Item -Path $statePath -Force -ErrorAction SilentlyContinue } catch {}

if ($OpenFolder) {
    Start-Process -FilePath explorer.exe -ArgumentList @('/select,', $local)
}

Write-Host 'OK' -ForegroundColor Green
