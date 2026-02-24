param(
    [string]$PixelIp = "",
    [string]$AdbPort = "",
    [string]$DeviceSerial = "",
    [switch]$NoAdbConnect,
    [switch]$Portrait
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($PixelIp)) {
    if ($env:PIXEL7_TAILSCALE_IP) {
        $PixelIp = $env:PIXEL7_TAILSCALE_IP
    } elseif ($env:PIXEL7_IP) {
        $PixelIp = $env:PIXEL7_IP
    } else {
        $PixelIp = '100.84.2.125'
    }
}

if ([string]::IsNullOrWhiteSpace($AdbPort)) {
    if ($env:PIXEL7_ADB_PORT) {
        $AdbPort = $env:PIXEL7_ADB_PORT
    } else {
        $AdbPort = '5555'
    }
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = ('{0}:{1}' -f $PixelIp, $AdbPort)
}

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

Write-Host '=== Pixel7 画面ミラー（無線 scrcpy）===' -ForegroundColor Cyan
Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Gray

if (-not $NoAdbConnect) {
    # DeviceSerial が host:port の場合は、そちらを優先して connect する（envのポートとズレても安定）
    $connectTarget = ('{0}:{1}' -f $PixelIp, $AdbPort)
    if ($DeviceSerial -match '^[0-9.]+:\d+$') {
        $connectTarget = $DeviceSerial
    }
    Write-Host ('[1/2] adb connect {0} ...' -f $connectTarget) -ForegroundColor Cyan
    $connectOut = (& $adbExe connect $connectTarget 2>&1 | Out-String)
    if (-not [string]::IsNullOrWhiteSpace($connectOut)) {
        $connectOut.TrimEnd() | Out-Host
    }

    # フォールバック: Tailscale(100.x) が切れている等で繋がらない場合、USB接続があれば wlan0 のIPv4を拾って再接続
    if (($connectTarget -match '^100\.') -and ($connectOut -match 'cannot connect|failed|10060|10061')) {
        $devicesRaw = (& $adbExe devices | Out-String)
        $usbSerial = ($devicesRaw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
                $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
            } | Select-Object -First 1) -replace '\s+device$',''
        if (-not [string]::IsNullOrWhiteSpace($usbSerial)) {
            try {
                $wlanLine = (& $adbExe -s $usbSerial shell "ip -f inet addr show wlan0 | grep -E 'inet ' || true" | Out-String).Trim()
                if ($wlanLine -match 'inet\s+([0-9.]+)/') {
                    $wifiIp = $Matches[1]
                    $wifiTarget = ('{0}:{1}' -f $wifiIp, $AdbPort)
                    Write-Host ('Tailscaleが見えないため、Wi-Fi側へフォールバックします: {0}' -f $wifiTarget) -ForegroundColor Yellow
                    (& $adbExe connect $wifiTarget 2>&1 | Out-String).TrimEnd() | Out-Host
                    $DeviceSerial = $wifiTarget
                    $connectTarget = $wifiTarget
                }
            } catch {
                # ignore and continue to device check
            }
        }
    }
    Start-Sleep -Seconds 1
}

Write-Host '[2/2] device check ...' -ForegroundColor Cyan
$devicesText = (& $adbExe devices | Out-String)
$pattern = [regex]::Escape($DeviceSerial) + '\s+device'
if ($devicesText -notmatch $pattern) {
    Write-Host ''
    Write-Host ('接続が確認できませんでした: {0}' -f $DeviceSerial) -ForegroundColor Yellow
    Write-Host '- Pixel側: 開発者向けオプション > Wireless debugging をON' -ForegroundColor Yellow
    Write-Host '- 初回はペアリングが必要: .\manaos_integrations\scripts\setup_pixel7_wireless_debugging.ps1' -ForegroundColor Yellow
    Write-Host '- ポートが変わった場合は PIXEL7_ADB_PORT を更新（端末表示のポートを使用）' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '現在のadb devices:' -ForegroundColor Gray
    Write-Host $devicesText
    exit 2
}

Write-Host 'scrcpy を起動します...' -ForegroundColor Green
$scrcpyArgs = @('-s', $DeviceSerial)
if ($Portrait) {
    # scrcpy v3.3+ は --capture-orientation。'@' 付きは回転ロック。
    # Pixel(スマホ)の自然方向は通常 portrait なので @0 で縦長固定になる。
    $scrcpyArgs += '--capture-orientation=@0'
}
Start-Process -FilePath $scrcpyExe -WorkingDirectory $scrcpyDir -ArgumentList $scrcpyArgs
