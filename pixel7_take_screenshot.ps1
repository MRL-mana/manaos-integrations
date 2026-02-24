param(
    [string]$DeviceSerial = "",
    [string]$OutDir = "",
    [switch]$OpenFolder
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

function Pick-DefaultSerial {
    $txt = Get-DevicesText

    if ($env:PIXEL7_ADB_SERIAL -and ($txt -match ([regex]::Escape($env:PIXEL7_ADB_SERIAL) + '\s+device'))) {
        return $env:PIXEL7_ADB_SERIAL
    }

    # まず「今つながっている無線 tcpip (IP:5555)」を優先
    $wirelessLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '^[0-9.]+:5555\s+device$'
        } | Select-Object -First 1)
    if ($wirelessLine) {
        return ($wirelessLine -replace '\s+device$','')
    }

    # 環境変数のWi-Fi IPがある場合はそれも優先候補に
    if ($env:PIXEL7_WIFI_IP) {
        $cand = ('{0}:5555' -f $env:PIXEL7_WIFI_IP)
        if ($txt -match ([regex]::Escape($cand) + '\s+device')) { return $cand }
    }

    foreach ($cand in @('100.84.2.125:5555')) {
        if ($txt -match ([regex]::Escape($cand) + '\s+device')) { return $cand }
    }

    $usbLine = ($txt -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
            $_ -match '\s+device$' -and $_ -notmatch ':' -and $_ -notmatch '^List of devices' -and $_ -notmatch '^emulator-'
        } | Select-Object -First 1)
    if ($usbLine) { return ($usbLine -replace '\s+device$','') }

    return ""
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Pick-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。先に「Pixel7 無線ADB復旧（5555）」を実行してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $env:USERPROFILE 'Desktop\screenshots'
}
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$outFile = Join-Path $OutDir ("pixel7_screenshot_{0}.png" -f $ts)

Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Cyan
Write-Host ('Save:   {0}' -f $outFile) -ForegroundColor Green

# バイナリを確実に保存するため cmd のリダイレクトを使用
$cmd = '"{0}" -s {1} exec-out screencap -p > "{2}"' -f $adbExe, $DeviceSerial, $outFile
cmd /c $cmd | Out-Null

if (-not (Test-Path $outFile)) {
    Write-Host 'スクショ保存に失敗しました。' -ForegroundColor Yellow
    exit 3
}

if ($OpenFolder) {
    Start-Process -FilePath explorer.exe -ArgumentList @('/select,', $outFile)
}

Write-Host 'OK' -ForegroundColor Green
