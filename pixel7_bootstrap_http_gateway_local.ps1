param(
    [string]$DeviceSerial = "",
    [int]$HostPort = 18000,
    [int]$SleepMs = 400,
    [int]$InstallWaitSec = 120
)

$ErrorActionPreference = 'Stop'

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
    Write-Host 'デバイスが見つかりません。先にADB接続（USB/無線）を確認してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

$root = $PSScriptRoot
$bootstrap = Join-Path $root 'pixel7_termux_bootstrap_http_gateway.ps1'

if (-not (Test-Path $bootstrap)) { throw "not found: $bootstrap" }

foreach ($p in @(
        (Join-Path $root 'pixel7_api_gateway.py'),
        (Join-Path $root 'termux\start_pixel7_api_gateway.sh'),
        (Join-Path $root 'termux\boot_start_pixel7_api_gateway.sh'),
        (Join-Path $root '.pixel7_api_token.txt')
    )) {
    if (-not (Test-Path $p)) {
        throw "required file not found (served by http.server): $p"
    }
}

if ($HostPort -lt 1024) { throw "HostPort must be >= 1024 (got: $HostPort)" }
if ($HostPort -gt 65535) { throw "HostPort must be <= 65535 (got: $HostPort)" }

Write-Host '=== Pixel7 HTTP Gateway Bootstrap (Local http.server + adb reverse) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Port  : {0}" -f $HostPort) -ForegroundColor Gray
Write-Host ("Serve : {0}" -f $root) -ForegroundColor DarkGray

$serverProc = $null
try {
    $serverProc = Start-Process -FilePath 'python' -ArgumentList @('-m','http.server',"$HostPort",'--bind','127.0.0.1') -WorkingDirectory $root -PassThru -WindowStyle Hidden

    $ready = $false
    for ($i = 1; $i -le 20; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Method Head -TimeoutSec 2 -Uri ("http://127.0.0.1:{0}/pixel7_api_gateway.py" -f $HostPort) | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) {
        throw 'local http.server did not become ready'
    }

    & $adbExe -s $DeviceSerial reverse --remove "tcp:$HostPort" 2>$null | Out-Null
    & $adbExe -s $DeviceSerial reverse "tcp:$HostPort" "tcp:$HostPort" | Out-Null

    & powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap -DeviceSerial $DeviceSerial -HostPort $HostPort -ServerBase 'http://127.0.0.1' -SleepMs $SleepMs -InstallWaitSec $InstallWaitSec
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap failed (exit=$LASTEXITCODE)"
    }

    Write-Host 'OK (bootstrapped into Termux $HOME)' -ForegroundColor Green
} finally {
    try { & $adbExe -s $DeviceSerial reverse --remove "tcp:$HostPort" 2>$null | Out-Null } catch {}
    if ($serverProc -and -not $serverProc.HasExited) {
        try { Stop-Process -Id $serverProc.Id -Force } catch {}
    }
}
