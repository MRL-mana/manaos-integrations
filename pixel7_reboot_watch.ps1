param(
    [int]$IntervalSeconds = 30,
    [switch]$RemoteOnly,
    [switch]$RestartAdbOnStart
)

$ErrorActionPreference = 'Stop'

if ($IntervalSeconds -lt 5) { $IntervalSeconds = 5 }
if ($IntervalSeconds -gt 600) { $IntervalSeconds = 600 }

$pidFile = Join-Path $PSScriptRoot '.pixel7_reboot_watch.pid'
$statusFile = Join-Path $PSScriptRoot '.pixel7_reboot_watch.status.json'
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir ('pixel7_reboot_watch_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

function Write-Log([string]$msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $msg"
    $line | Out-Host
    Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
}

Set-Content -Path $pidFile -Value $PID -Encoding ASCII
Write-Log "=== Pixel7 reboot watch started (PID=$PID, interval=${IntervalSeconds}s) ==="

$recover = Join-Path $PSScriptRoot 'pixel7_adb_recover_wireless.ps1'
$collect = Join-Path $PSScriptRoot 'pixel7_collect_reboot_logs.ps1'

if (-not (Test-Path $recover)) { Write-Log "ERROR: not found: $recover"; exit 2 }
if (-not (Test-Path $collect)) { Write-Log "ERROR: not found: $collect"; exit 2 }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'
if (-not (Test-Path $adbExe)) { Write-Log "ERROR: adb.exe not found"; exit 2 }

function Get-DevicesText { return (& $adbExe devices | Out-String) }
function Get-DefaultSerial {
    $txt = Get-DevicesText
    if ($env:PIXEL7_ADB_SERIAL -and ($txt -match ([regex]::Escape($env:PIXEL7_ADB_SERIAL) + '\s+device'))) { return $env:PIXEL7_ADB_SERIAL }
    $wirelessLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^[0-9.]+:5555\s+device$' } | Select-Object -First 1)
    if ($wirelessLine) { return ($wirelessLine -replace '\s+device$','') }
    $usbLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-' } | Select-Object -First 1)
    if ($usbLine) { return ($usbLine -replace '\s+device$','') }
    return ""
}
function Run-Shell([string]$serial,[string]$cmd) { return (& $adbExe -s $serial shell $cmd 2>&1 | Out-String).Trim() }

$lastBootId = $null
$pendingBootId = $null
$pendingSince = $null
$first = $true

while ($true) {
    try {
        if ($first -and $RestartAdbOnStart) {
            if ($RemoteOnly) { & $recover -RestartAdb -RemoteOnly | Out-Null } else { & $recover -RestartAdb | Out-Null }
        } else {
            if ($RemoteOnly) { & $recover -RemoteOnly | Out-Null } else { & $recover | Out-Null }
        }
        $first = $false
    } catch {
        Write-Log ("recover error: {0}" -f $_.Exception.Message)
    }

    $serial = Get-DefaultSerial
    if ([string]::IsNullOrWhiteSpace($serial)) {
        Write-Log 'no device'
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    $bootId = Run-Shell $serial 'cat /proc/sys/kernel/random/boot_id'
    $bootCompleted = Run-Shell $serial 'getprop sys.boot_completed'

    if (-not $lastBootId) {
        $lastBootId = $bootId
        Write-Log ("init boot_id={0} serial={1}" -f $bootId, $serial)
    } elseif ($bootId -and ($bootId -ne $lastBootId)) {
        if (-not $pendingBootId -or $pendingBootId -ne $bootId) {
            $pendingBootId = $bootId
            $pendingSince = Get-Date
            Write-Log ("reboot detected boot_id={0} (prev={1}) serial={2}" -f $bootId, $lastBootId, $serial)
        }
    }

    if ($pendingBootId) {
        # 起動完了まで少し待つ（取れる情報が増える）
        if ($bootCompleted -ne '1') {
            $age = (Get-Date) - $pendingSince
            Write-Log ("boot not completed yet (age={0}s)" -f ([int]$age.TotalSeconds))
        } else {
            Write-Log 'collect reboot logs...'
            try {
                if ($RemoteOnly) { & $collect -DeviceSerial $serial -RemoteOnly | Out-Null } else { & $collect -DeviceSerial $serial | Out-Null }
                Write-Log 'collect done'
            } catch {
                Write-Log ("collect error: {0}" -f $_.Exception.Message)
            }
            $lastBootId = $pendingBootId
            $pendingBootId = $null
            $pendingSince = $null
        }
    }

    try {
        $status = [ordered]@{
            ts = (Get-Date).ToString('o')
            pid = $PID
            intervalSeconds = $IntervalSeconds
            remoteOnly = [bool]$RemoteOnly
            serial = $serial
            bootId = $bootId
            bootCompleted = $bootCompleted
            pendingBootId = $pendingBootId
        }
        ($status | ConvertTo-Json -Depth 4) | Set-Content -Encoding UTF8 -Path $statusFile
    } catch {}

    Start-Sleep -Seconds $IntervalSeconds
}
