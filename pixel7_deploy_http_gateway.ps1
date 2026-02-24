param(
    [string]$DeviceSerial = "",
    [string]$DestDir = "/sdcard/Download/manaos_pixel7_http"
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
    Write-Host 'デバイスが見つかりません。先に「Pixel7 無線ADB復旧（5555）」を実行してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

$srcGateway = Join-Path $PSScriptRoot 'pixel7_api_gateway.py'
$srcStart = Join-Path $PSScriptRoot 'termux\start_pixel7_api_gateway.sh'
$srcBoot = Join-Path $PSScriptRoot 'termux\boot_start_pixel7_api_gateway.sh'

foreach ($p in @($srcGateway,$srcStart,$srcBoot)) {
    if (-not (Test-Path $p)) { throw "not found: $p" }
}

Write-Host '=== Pixel7 Deploy HTTP Gateway (adb push) ===' -ForegroundColor Cyan
Write-Host ("Target: {0}" -f $DeviceSerial) -ForegroundColor Gray
Write-Host ("Dest  : {0}" -f $DestDir) -ForegroundColor Gray

& $adbExe -s $DeviceSerial shell "mkdir -p $DestDir" | Out-Null

& $adbExe -s $DeviceSerial push "$srcGateway" "$DestDir/pixel7_api_gateway.py" | Out-Host
& $adbExe -s $DeviceSerial push "$srcStart" "$DestDir/start_pixel7_api_gateway.sh" | Out-Host
& $adbExe -s $DeviceSerial push "$srcBoot" "$DestDir/boot_start_pixel7_api_gateway.sh" | Out-Host

Write-Host ''
Write-Host 'Next (on Pixel / Termux):' -ForegroundColor Yellow
Write-Host ("  cd $DestDir") -ForegroundColor White
Write-Host '  chmod +x start_pixel7_api_gateway.sh' -ForegroundColor White
Write-Host '  export PIXEL7_API_TOKEN=...; ./start_pixel7_api_gateway.sh' -ForegroundColor White
Write-Host ''
Write-Host 'Tip: use task "ManaOS: Pixel7 Termuxを開く（ADB / HTTP復旧用）" to bring Termux front.' -ForegroundColor DarkGray

Write-Host 'OK' -ForegroundColor Green
