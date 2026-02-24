param(
    [string]$DeviceSerial = "",
    [switch]$RemoteOnly
)

$ErrorActionPreference = 'Stop'

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

    return ""
}

function Invoke-AdbShellCommand([string]$cmd) {
    $old = $ErrorActionPreference
    try {
        # 権限不足等でstderrが出ても止めない（ログ回収はベストエフォート）
        $ErrorActionPreference = 'Continue'
        return (& $adbExe -s $DeviceSerial shell $cmd 2>&1 | Out-String)
    } finally {
        $ErrorActionPreference = $old
    }
}

function Set-TextFileSafely([string]$path, [string]$text) {
    $dir = Split-Path -Parent $path
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Set-Content -Path $path -Value $text -Encoding UTF8
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'device not found' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$baseDir = Join-Path $PSScriptRoot ("logs\\pixel7_reboots\\{0}_{1}" -f $ts, ($DeviceSerial -replace '[:\\/\\s]','_'))
New-Item -ItemType Directory -Path $baseDir -Force | Out-Null

Set-TextFileSafely (Join-Path $baseDir 'meta.txt') (
    "ts=$ts`nserial=$DeviceSerial`nremoteOnly=$RemoteOnly`n")

# 基本情報
Set-TextFileSafely (Join-Path $baseDir 'boot_id.txt') (Invoke-AdbShellCommand 'cat /proc/sys/kernel/random/boot_id')
Set-TextFileSafely (Join-Path $baseDir 'uptime.txt') (Invoke-AdbShellCommand 'cat /proc/uptime')
Set-TextFileSafely (Join-Path $baseDir 'getprop.txt') (Invoke-AdbShellCommand 'getprop')
Set-TextFileSafely (Join-Path $baseDir 'bootreason.txt') (
    (Invoke-AdbShellCommand 'getprop ro.boot.bootreason; getprop sys.boot.reason; getprop ro.boot.bootreason.last; getprop sys.boot.reason.last')
)

# logcat（直近のみ）
Set-TextFileSafely (Join-Path $baseDir 'logcat_all_tail.txt') (Invoke-AdbShellCommand 'logcat -b all -d -v threadtime -t 5000')

# dumpsys（取れれば）
Set-TextFileSafely (Join-Path $baseDir 'dumpsys_battery.txt') (Invoke-AdbShellCommand 'dumpsys battery')
Set-TextFileSafely (Join-Path $baseDir 'dumpsys_power.txt') (Invoke-AdbShellCommand 'dumpsys power')
Set-TextFileSafely (Join-Path $baseDir 'dumpsys_thermalservice.txt') (Invoke-AdbShellCommand 'dumpsys thermalservice')

# pstore / last_kmsg（取れない端末もあるのでベストエフォート）
Set-TextFileSafely (Join-Path $baseDir 'pstore_ls.txt') (Invoke-AdbShellCommand 'ls -1 /sys/fs/pstore 2>/dev/null || echo NO_PSTORE')

try {
    $ls = Invoke-AdbShellCommand 'ls -1 /sys/fs/pstore 2>/dev/null || true'
    $files = ($ls -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    foreach ($f in $files) {
        $safe = ($f -replace '[^a-zA-Z0-9._-]','_')
        Set-TextFileSafely (Join-Path $baseDir ("pstore_{0}.txt" -f $safe)) (Invoke-AdbShellCommand ("cat /sys/fs/pstore/{0} 2>/dev/null || echo NO_ACCESS" -f $f))
    }
} catch {}

    Set-TextFileSafely (Join-Path $baseDir 'last_kmsg.txt') (Invoke-AdbShellCommand 'cat /proc/last_kmsg 2>/dev/null || echo NO_LAST_KMSG')
    Set-TextFileSafely (Join-Path $baseDir 'dmesg_tail.txt') (Invoke-AdbShellCommand 'dmesg | tail -n 400')

Write-Host ("Saved: {0}" -f $baseDir) -ForegroundColor Green
