param(
    [string]$DeviceSerial = "",
    [switch]$AlsoWhitelistHttpShortcuts
)

$ErrorActionPreference = 'Stop'

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ("adb.exe が見つかりません: {0}" -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-DevicesText { return (& $adbExe devices | Out-String) }

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
    if ($usbLine) { return ($usbLine -replace '\s+device$','') }

    return ""
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

$pkgs = @('com.termux')
if ($AlsoWhitelistHttpShortcuts) { $pkgs += 'ch.rmy.android.http_shortcuts' }

Write-Host '=== Pixel7 Allow Termux Background ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Packages: {0}" -f ($pkgs -join ', ')) -ForegroundColor Gray

foreach ($pkg in $pkgs) {
    Write-Host ("[whitelist] {0}" -f $pkg) -ForegroundColor Gray
    & $adbExe -s $DeviceSerial shell "dumpsys deviceidle whitelist +$pkg" 2>$null | Out-Null

    # best-effort: allow background run (may be restricted on some builds)
    foreach ($op in @('RUN_IN_BACKGROUND','RUN_ANY_IN_BACKGROUND','WAKE_LOCK')) {
        try {
            & $adbExe -s $DeviceSerial shell "cmd appops set $pkg $op allow" 2>$null | Out-Null
        } catch {}
    }
}

Write-Host '[verify] deviceidle whitelist (filtered)' -ForegroundColor Gray
$wl = (& $adbExe -s $DeviceSerial shell 'dumpsys deviceidle whitelist' 2>&1 | Out-String)
$wl.Split("`n") | Where-Object { $line=$_; $pkgs | Where-Object { $line -match [regex]::Escape($_) } } | ForEach-Object { $_.TrimEnd() } | Out-Host

Write-Host 'OK' -ForegroundColor Green
