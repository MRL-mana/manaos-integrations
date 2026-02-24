param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Home',
        'Back',
        'Recents',
        'UnlockSwipe',
        'Wake',
        'Power',
        'VolumeUp',
        'VolumeDown',
        'VolumeMute',
        'ExpandNotifications',
        'ExpandQuickSettings',
        'CollapseStatusBar',
        'OpenSettings',
        'OpenWifiSettings',
        'OpenTailscale',
        'OpenAppInfoTailscale',
        'OpenBatteryOptimizationSettings',
        'OpenDeveloperOptions',
        'EnableStayAwakeOnCharge',
        'DisableStayAwakeOnCharge',
        'DisableDoze',
        'EnableDoze',
        'OpenVpnSettings',
        'OpenDefaultAppsSettings',
        'OpenAppInfoChrome',
        'OpenAppInfoBrave',
        'OpenHttpShortcuts',
        'OpenTermux',
        'OpenChrome',
        'OpenOpenWebUI'
    )]
    [string]$Action,

    [string]$DeviceSerial = "",

    [string]$Url = "",

    [int]$Repeat = 1
)

$ErrorActionPreference = 'Stop'

if ($Repeat -lt 1) { $Repeat = 1 }
if ($Repeat -gt 5) { $Repeat = 5 }

$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'

if (-not (Test-Path $adbExe)) {
    Write-Host ('adb.exe が見つかりません: {0}' -f $adbExe) -ForegroundColor Red
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

function Get-ScreenSizeOrDefault {
    $w = 1080
    $h = 2400
    try {
        $out = (& $adbExe -s $DeviceSerial shell 'wm size' 2>&1 | Out-String)
        if ($out -match 'Physical size:\s*(\d+)x(\d+)') {
            $w = [int]$Matches[1]
            $h = [int]$Matches[2]
        }
    } catch {}
    return @($w, $h)
}

function Test-CmdStatusbar([string]$cmd) {
    try {
        & $adbExe -s $DeviceSerial shell "cmd statusbar $cmd" | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Invoke-AdbShell([string]$cmd) {
    & $adbExe -s $DeviceSerial shell $cmd | Out-Null
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

function Get-OpenWebUiUrl {
    if ($env:OPENWEBUI_URL) {
        return $env:OPENWEBUI_URL.TrimEnd('/')
    }

    $statusPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'manaos_integrations\logs\openwebui_tailscale_status.json'
    if (-not (Test-Path $statusPath)) {
        # スクリプト直下実行も考慮
        $statusPath = Join-Path $PSScriptRoot 'logs\openwebui_tailscale_status.json'
    }
    if (-not (Test-Path $statusPath)) {
        return 'http://127.0.0.1:3001'
    }

    try {
        $obj = Get-Content -Raw -Encoding UTF8 $statusPath | ConvertFrom-Json
        if ($obj.tailscale_https_url) { return ([string]$obj.tailscale_https_url).TrimEnd('/') }
        if ($obj.tailscale_ip_url) { return ([string]$obj.tailscale_ip_url).TrimEnd('/') }
    } catch {}

    return 'http://127.0.0.1:3001'
}

function Start-ViewUrl([string]$url, [string]$package) {
    if ([string]::IsNullOrWhiteSpace($url)) { return }

    if (-not [string]::IsNullOrWhiteSpace($package)) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $out = (& $adbExe -s $DeviceSerial shell "am start --user 0 -a android.intent.action.VIEW -d $url -p $package" 2>&1 | Out-String).Trim()
        } finally {
            $ErrorActionPreference = $prev
        }
        if ($out -match 'Error: Activity not started') {
            # fallback
            (& $adbExe -s $DeviceSerial shell "am start --user 0 -a android.intent.action.VIEW -d $url" 2>&1 | Out-String).TrimEnd() | Out-Host
            return
        }
        if ($out) { $out | Out-Host }
        return
    }

    (& $adbExe -s $DeviceSerial shell "am start --user 0 -a android.intent.action.VIEW -d $url" 2>&1 | Out-String).TrimEnd() | Out-Host
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = Get-DefaultSerial
}

if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    Write-Host 'デバイスが見つかりません。先に「Pixel7 無線ADB復旧（5555）」を実行してください。' -ForegroundColor Yellow
    Write-Host (Get-DevicesText) -ForegroundColor Gray
    exit 2
}

Write-Host ('Target: {0}' -f $DeviceSerial) -ForegroundColor Cyan
Write-Host ('Action: {0} (x{1})' -f $Action, $Repeat) -ForegroundColor Gray

for ($i = 0; $i -lt $Repeat; $i++) {
    switch ($Action) {
        'Home' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_HOME' | Out-Null
        }
        'Back' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_BACK' | Out-Null
        }
        'Recents' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_APP_SWITCH' | Out-Null
        }
        'UnlockSwipe' {
            # PIN/パターン入力はしない（安全）。画面点灯→上スワイプまで。
            & $adbExe -s $DeviceSerial shell 'input keyevent 224' | Out-Null
            Start-Sleep -Milliseconds 200
            $size = Get-ScreenSizeOrDefault
            $x = [int]($size[0] / 2)
            $y1 = [int]($size[1] * 0.85)
            $y2 = [int]($size[1] * 0.25)
            & $adbExe -s $DeviceSerial shell "input swipe $x $y1 $x $y2 250" | Out-Null
        }
        'Wake' {
            # 224 = KEYCODE_WAKEUP
            & $adbExe -s $DeviceSerial shell 'input keyevent 224' | Out-Null
        }
        'Power' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_POWER' | Out-Null
        }
        'VolumeUp' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_VOLUME_UP' | Out-Null
        }
        'VolumeDown' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_VOLUME_DOWN' | Out-Null
        }
        'VolumeMute' {
            & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_MUTE' | Out-Null
        }
        'ExpandNotifications' {
            if (-not (Test-CmdStatusbar 'expand-notifications')) {
                $size = Get-ScreenSizeOrDefault
                $x = [int]($size[0] / 2)
                $y1 = 5
                $y2 = [int]($size[1] * 0.6)
                & $adbExe -s $DeviceSerial shell "input swipe $x $y1 $x $y2 250" | Out-Null
            }
        }
        'ExpandQuickSettings' {
            if (-not (Test-CmdStatusbar 'expand-settings')) {
                $size = Get-ScreenSizeOrDefault
                $x = [int]($size[0] / 2)
                $y1 = 5
                $y2 = [int]($size[1] * 0.75)
                & $adbExe -s $DeviceSerial shell "input swipe $x $y1 $x $y2 250" | Out-Null
                Start-Sleep -Milliseconds 200
                & $adbExe -s $DeviceSerial shell "input swipe $x $y1 $x $y2 250" | Out-Null
            }
        }
        'CollapseStatusBar' {
            if (-not (Test-CmdStatusbar 'collapse')) {
                & $adbExe -s $DeviceSerial shell 'input keyevent KEYCODE_BACK' | Out-Null
            }
        }
        'OpenSettings' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.SETTINGS' | Out-Null
        }
        'OpenWifiSettings' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.WIFI_SETTINGS' | Out-Null
        }
        'OpenTailscale' {
            $pkg = 'com.tailscale.ipn'
            Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
        }
        'OpenAppInfoTailscale' {
            & $adbExe -s $DeviceSerial shell "am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.tailscale.ipn" | Out-Null
        }
        'OpenBatteryOptimizationSettings' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.IGNORE_BATTERY_OPTIMIZATION_SETTINGS' | Out-Null
        }
        'OpenDeveloperOptions' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.DEVELOPMENT_SETTINGS' | Out-Null
        }
        'EnableStayAwakeOnCharge' {
            # 充電中に画面を消さない（開発者オプション相当）
            Invoke-AdbShell 'settings put global stay_on_while_plugged_in 3'
        }
        'DisableStayAwakeOnCharge' {
            Invoke-AdbShell 'settings put global stay_on_while_plugged_in 0'
        }
        'DisableDoze' {
            # 一時的にDoze/デバイスアイドルを無効化（再起動で戻る場合あり）
            Invoke-AdbShell 'dumpsys deviceidle disable'
        }
        'EnableDoze' {
            Invoke-AdbShell 'dumpsys deviceidle enable'
        }
        'OpenVpnSettings' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.VPN_SETTINGS' | Out-Null
        }
        'OpenDefaultAppsSettings' {
            & $adbExe -s $DeviceSerial shell 'am start -a android.settings.MANAGE_DEFAULT_APPS_SETTINGS' | Out-Null
        }
        'OpenAppInfoChrome' {
            & $adbExe -s $DeviceSerial shell "am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.android.chrome" | Out-Null
        }
        'OpenAppInfoBrave' {
            & $adbExe -s $DeviceSerial shell "am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.brave.browser" | Out-Null
        }
        'OpenHttpShortcuts' {
            $pkg = 'ch.rmy.android.http_shortcuts'
            Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
        }
        'OpenTermux' {
            $pkg = 'com.termux'
            Invoke-AdbShellBestEffort "monkey -p $pkg -c android.intent.category.LAUNCHER 1"
        }
        'OpenChrome' {
            if ([string]::IsNullOrWhiteSpace($Url)) {
                $Url = 'https://example.com'
            }
            Start-ViewUrl $Url 'com.android.chrome'
        }
        'OpenOpenWebUI' {
            $web = Get-OpenWebUiUrl
            Start-ViewUrl $web 'com.android.chrome'
        }
    }

    Start-Sleep -Milliseconds 150
}

Write-Host 'OK' -ForegroundColor Green
