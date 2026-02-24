param(
    [string]$DeviceSerial = "",
    [string]$PixelTailscaleIp = "",
    [string]$AdbPort = "",
    [switch]$NoAdbConnect,
    [switch]$Portrait,
    [switch]$Landscape,
    [switch]$KillExisting,
    [switch]$RemoteOnly,
    [switch]$Wait,
    [switch]$TurnScreenOff
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($PixelTailscaleIp)) {
    # MagicDNSホスト名があれば優先（外出でIPが変わっても追従しやすい）
    if ($env:PIXEL7_TAILSCALE_HOST) {
        $PixelTailscaleIp = $env:PIXEL7_TAILSCALE_HOST
    } else {
        $PixelTailscaleIp = if ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } else { '100.84.2.125' }
    }
}
if ([string]::IsNullOrWhiteSpace($AdbPort)) {
    $AdbPort = if ($env:PIXEL7_ADB_PORT) { $env:PIXEL7_ADB_PORT } else { '' }
}

# Wireless debugging のペアリングポート(ランダム)と、tcpip(5555) の両方を試す
# ただし安定運用は tcpip(5555) が優先
$portCandidates = @('5555')
if (-not [string]::IsNullOrWhiteSpace($AdbPort) -and $AdbPort -ne '5555') { $portCandidates += $AdbPort }
if ($env:PIXEL7_ADB_PORT -and $env:PIXEL7_ADB_PORT -ne '5555' -and $env:PIXEL7_ADB_PORT -ne $AdbPort) { $portCandidates += $env:PIXEL7_ADB_PORT }
$portCandidates = $portCandidates | Select-Object -Unique

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'
$scrcpyExe = Join-Path $scrcpyDir 'scrcpy.exe'

if (-not (Test-Path $scrcpyExe)) {
    Write-Host ('scrcpy.exe が見つかりません: {0}' -f $scrcpyExe) -ForegroundColor Red
    Write-Host 'セットアップ: Scripts\scrcpy_guide.md を参照' -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path $adbExe)) {
    Write-Host ('adb.exe が見つかりません: {0}' -f $adbExe) -ForegroundColor Red
    exit 1
}

function Get-AdbDevicesText {
    return (& $adbExe devices | Out-String)
}

function Find-UsbDeviceSerial {
    $devicesRaw = Get-AdbDevicesText
    $usbSerial = ($devicesRaw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
        } | Select-Object -First 1) -replace '\s+device$',''
    return $usbSerial
}

function Test-AdbConnect([string]$target) {
    if ($NoAdbConnect) { return $true }
    Write-Host ('adb connect {0} ...' -f $target) -ForegroundColor Cyan
    $out = (& $adbExe connect $target 2>&1 | Out-String).Trim()
    if ($out) { $out | Out-Host }
    Start-Sleep -Milliseconds 600

    $devicesText = Get-AdbDevicesText
    $pattern = [regex]::Escape($target) + '\s+device'
    return ($devicesText -match $pattern)
}

function Get-WifiTargetViaUsb([string]$port) {
    $usbSerial = Find-UsbDeviceSerial
    if ([string]::IsNullOrWhiteSpace($usbSerial)) { return "" }

    try {
        # Tailscaleが無い/死んでる時のためのLANフォールバック
        $wlanLine = (& $adbExe -s $usbSerial shell "ip -f inet addr show wlan0 | grep -E 'inet ' || true" | Out-String).Trim()
        if ($wlanLine -match 'inet\s+([0-9.]+)/') {
            return ('{0}:{1}' -f $Matches[1], $port)
        }
    } catch {
        return ""
    }
    return ""
}

Write-Host '=== Pixel7 画面ミラー（scrcpy 自動）===' -ForegroundColor Cyan

if ($KillExisting) {
    Stop-Process -Name scrcpy -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 200
}

$candidates = @()

if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $candidates += $DeviceSerial
} elseif ($env:PIXEL7_ADB_SERIAL) {
    $candidates += $env:PIXEL7_ADB_SERIAL
} else {
    if (-not $RemoteOnly) {
        # USBが見えるなら最優先（無線より安定）
        $usbSerial = Find-UsbDeviceSerial
        if (-not [string]::IsNullOrWhiteSpace($usbSerial)) {
            $candidates += $usbSerial
        }

        # 直近に adb devices に出ている無線ターゲット（device/offline）も候補に入れる
        try {
            $devicesText = Get-AdbDevicesText
            $known = ($devicesText -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
                    $_ -match '^[0-9.]+:\d+\s+(device|offline)$'
                } | ForEach-Object {
                    ($_ -split '\s+')[0]
                })
            foreach ($k in $known) {
                if (-not [string]::IsNullOrWhiteSpace($k)) { $candidates += $k }
            }
        } catch {}
    }

    foreach ($port in $portCandidates) {
        $candidates += ('{0}:{1}' -f $PixelTailscaleIp, $port)
    }

    if (-not $RemoteOnly) {
        $wifiIp = if ($env:PIXEL7_WIFI_IP) { $env:PIXEL7_WIFI_IP } else { "" }
        if (-not [string]::IsNullOrWhiteSpace($wifiIp)) {
            foreach ($port in $portCandidates) {
                $candidates += ('{0}:{1}' -f $wifiIp, $port)
            }
        } else {
            foreach ($port in $portCandidates) {
                $wifiTarget = Get-WifiTargetViaUsb $port
                if (-not [string]::IsNullOrWhiteSpace($wifiTarget)) {
                    $candidates += $wifiTarget
                }
            }
        }

        # USBは先頭で追加済み
    }
}

# 重複除去
$candidates = $candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

Write-Host ('Candidates: {0}' -f ($candidates -join ', ')) -ForegroundColor Gray

$selected = $null
foreach ($cand in $candidates) {
    if ($cand -match '^[0-9.]+:\d+$') {
        if (Test-AdbConnect $cand) {
            $selected = $cand
            break
        }
    } else {
        # USB serial の場合
        $devicesText = Get-AdbDevicesText
        $pattern = [regex]::Escape($cand) + '\s+device'
        if ($devicesText -match $pattern) {
            $selected = $cand
            break
        }
    }
}

if (-not $selected) {
    Write-Host '接続できるデバイスが見つかりませんでした。' -ForegroundColor Yellow
    Write-Host (Get-AdbDevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host ("Selected: {0}" -f $selected) -ForegroundColor Green

# USBが選ばれた場合はtcpip接続を切って安定化（複数トランスポート競合回避）
if ($selected -notmatch ':') {
    try {
        & $adbExe disconnect | Out-Null
        Start-Sleep -Milliseconds 250
    } catch {}
}

if ($Portrait -and $Landscape) {
    Write-Host 'Portrait と Landscape は同時指定できません。' -ForegroundColor Yellow
    exit 3
}

$argsString = "-s $selected"
if ($Portrait) {
    $argsString += " --capture-orientation=@0"
} elseif ($Landscape) {
    $argsString += " --capture-orientation=@90"
}

# 切断しやすい環境向けの安定化オプション
$argsString += ' --force-adb-forward'
$argsString += ' --stay-awake'
$argsString += ' --no-audio'
$argsString += ' --verbosity=debug'

# Android 16 + hw encoder で不安定な場合があるため、まずはSWエンコーダで安定化
$argsString += ' --video-codec=h264'
$argsString += ' --video-encoder=c2.android.avc.encoder'
$argsString += ' --max-fps=30'

if ($RemoteOnly) {
    # 外出先は帯域/負荷を抑える（必要なら後で調整）
    $argsString += ' --max-size=1024'
    $argsString += ' --bit-rate=4M'
}

if ($TurnScreenOff) {
    # 端末の画面を消して発熱/バッテリーを抑える（ミラーはPC側で見える）
    $argsString += ' --turn-screen-off'
}

$logsDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$outLog = Join-Path $logsDir ("scrcpy_auto_{0}.out.log" -f $ts)
$errLog = Join-Path $logsDir ("scrcpy_auto_{0}.err.log" -f $ts)

Write-Host ("scrcpy: {0}" -f $scrcpyExe) -ForegroundColor Gray
Write-Host ("args : {0}" -f $argsString) -ForegroundColor Gray
Write-Host ("log  : {0}" -f $errLog) -ForegroundColor DarkGray

$p = Start-Process -FilePath $scrcpyExe -WorkingDirectory $scrcpyDir -ArgumentList $argsString -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru

Start-Sleep -Milliseconds 1200
try { $p.Refresh() } catch {}

if ($p.HasExited) {
    Write-Host ("scrcpy が起動直後に終了しました (exit={0})" -f $p.ExitCode) -ForegroundColor Yellow
    if (Test-Path $errLog) {
        Write-Host '--- scrcpy stderr (tail) ---' -ForegroundColor DarkYellow
        Get-Content -Path $errLog -Tail 80 -ErrorAction SilentlyContinue | Out-Host
    }
    exit 5
}

Write-Host ("scrcpy started (pid={0})" -f $p.Id) -ForegroundColor Green

if ($Wait) {
    try {
        Wait-Process -Id $p.Id
        $p.Refresh()
        Write-Host ("scrcpy exited (exit={0})" -f $p.ExitCode) -ForegroundColor Yellow
        exit $p.ExitCode
    } catch {
        Write-Host ("scrcpy wait failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        exit 6
    }
}
