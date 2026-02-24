param(
    [string]$DeviceSerial = "",
    [int]$SleepMs = 300
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

function Invoke-AdbShellBestEffort([string]$cmd) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $adbExe
    $psi.Arguments = ("-s {0} shell {1}" -f $DeviceSerial, $cmd)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    if ($p) {
        try {
            $null = $p.StandardOutput.ReadToEnd()
            $null = $p.StandardError.ReadToEnd()
            $p.WaitForExit()
        } catch {}
    }
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。先にADB接続（USB/無線）を確認してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host '=== Pixel7 Termux Setup Storage (termux-setup-storage) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray

# Bring Termux to front
$pkg = 'com.termux'
Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
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

Send-TermuxLine 'termux-setup-storage'

Write-Host ''
Write-Host '[NEXT] Pixelの画面にストレージ権限の許可ダイアログが出たら「許可」をタップしてください。' -ForegroundColor Yellow
Write-Host '完了後、/sdcard/Download へのログ出力やファイル共有が安定します。' -ForegroundColor Gray
Write-Host 'OK (command sent)' -ForegroundColor Green
