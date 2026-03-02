param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'OpenUrl',
        'OpenOpenWebUI',
        'OpenHttpShortcuts',
        'Wake',
        'Home',
        'Back',
        'Recents',
        'ExpandNotifications',
        'ExpandQuickSettings',
        'CollapseStatusBar'
    )]
    [string]$Action,

    [ValidateSet('HTTPFirst', 'ADBFirst', 'HTTPOnly', 'ADBOnly')]
    [string]$Mode = 'HTTPFirst',

    [string]$DeviceSerial = "",

    [string]$Url = "",

    [int]$TimeoutSec = 5
)

$ErrorActionPreference = 'Stop'

$http = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$adb = Join-Path $PSScriptRoot 'pixel7_remote_control.ps1'

$useLocalHttp = $false
try {
    $scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
    $adbExe = Join-Path $scrcpyDir 'adb.exe'
    if (Test-Path $adbExe) {
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

        $serial = if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) { $DeviceSerial } else { Get-DefaultSerial }
        if ($serial) {
            & $adbExe -s $serial forward --remove tcp:5122 2>$null | Out-Null
            & $adbExe -s $serial forward tcp:5122 tcp:5122 2>$null | Out-Null
        } else {
            & $adbExe forward --remove tcp:5122 2>$null | Out-Null
            & $adbExe forward tcp:5122 tcp:5122 2>$null | Out-Null
        }
        $r = Invoke-RestMethod -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:5122/health'
        if ($r -and ($r.status -eq 'healthy')) { $useLocalHttp = $true }
    }
} catch {
    $useLocalHttp = $false
}

function Invoke-Http([string]$httpAction, [hashtable]$extraArgs = @{}) {
    if (-not (Test-Path $http)) { throw "pixel7_http_control.ps1 not found: $http" }

    $callArgs = @{
        Action = $httpAction
        TimeoutSec = $TimeoutSec
    }
    if ($useLocalHttp) {
        $callArgs.PixelHost = '127.0.0.1'
        $callArgs.Port = 5122
    }

    foreach ($k in $extraArgs.Keys) {
        $callArgs[$k] = $extraArgs[$k]
    }

    $out = & $http @callArgs 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw ("HTTP action failed (exit={0})" -f $exitCode)
    }
    return $out
}

function Invoke-Adb([string]$adbAction, [hashtable]$extraArgs = @{}) {
    if (-not (Test-Path $adb)) { throw "pixel7_remote_control.ps1 not found: $adb" }

    $callArgs = @{
        Action = $adbAction
    }
    if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
        $callArgs.DeviceSerial = $DeviceSerial
    }
    foreach ($k in $extraArgs.Keys) {
        $callArgs[$k] = $extraArgs[$k]
    }

    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $adb @callArgs 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw ("ADB action failed (exit={0})" -f $exitCode)
        }
    } finally {
        $ErrorActionPreference = $prev
    }
    return $out
}

function Invoke-StepAttempt([scriptblock]$fn) {
    try {
        $s = & $fn
        if ($s) { $s.TrimEnd() | Out-Host }
        return $true
    } catch {
        Write-Host ("[WARN] {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        return $false
    }
}

function Resolve-HttpBaseUrl {
    if ($useLocalHttp) {
        return 'http://127.0.0.1:5122'
    }
    if ($env:PIXEL7_API_BASE) {
        return $env:PIXEL7_API_BASE.TrimEnd('/')
    }
    $host = if ($env:PIXEL7_API_HOST) { $env:PIXEL7_API_HOST } elseif ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } elseif ($env:PIXEL7_IP) { $env:PIXEL7_IP } else { '100.84.2.125' }
    $port = if ($env:PIXEL7_API_PORT) { $env:PIXEL7_API_PORT } else { '5122' }
    return ("http://{0}:{1}" -f $host, $port)
}

function Get-Pixel7ApiProfile {
    try {
        $base = Resolve-HttpBaseUrl
        $root = Invoke-RestMethod -UseBasicParsing -TimeoutSec 2 ($base + '/')
        return [string]$root.api_profile
    } catch {
        return ''
    }
}

Write-Host ("=== Pixel7 Control (HTTP→ADB): {0} mode={1} ===" -f $Action, $Mode) -ForegroundColor Cyan
if ($useLocalHttp) {
    Write-Host 'HTTP: using localhost (adb forward) http://127.0.0.1:5122' -ForegroundColor DarkGray
}

$adbFirst = $Mode -in @('ADBFirst','ADBOnly')
$httpAllowed = $Mode -notin @('ADBOnly')
$adbAllowed = $Mode -notin @('HTTPOnly')

if ($Mode -eq 'HTTPFirst') {
    $profile = Get-Pixel7ApiProfile
    if ($profile -and $profile -ne 'full') {
        Write-Host ("[INFO] HTTP skipped: PIXEL7_API_PROFILE={0}. switching to ADB-first fallback." -f $profile) -ForegroundColor Yellow
        $adbFirst = $true
    }
}

$httpPlan = @()
$adbPlan = @()

switch ($Action) {
    'OpenUrl' {
        if ([string]::IsNullOrWhiteSpace($Url)) { throw "-Url is required" }
        $httpPlan += { Invoke-Http 'OpenUrl' @{ Url = $Url } }
        $adbPlan += { Invoke-Adb 'OpenChrome' @{ Url = $Url } }
    }
    'OpenOpenWebUI' {
        $httpPlan += { Invoke-Http 'OpenOpenWebUI' }
        $adbPlan += { Invoke-Adb 'OpenOpenWebUI' }
    }
    'OpenHttpShortcuts' {
        # HTTP: open app by package (Pixel側Termuxでmonkey)
        $httpPlan += { Invoke-Http 'OpenApp' @{ Package = 'ch.rmy.android.http_shortcuts' } }
        $adbPlan += { Invoke-Adb 'OpenHttpShortcuts' }
    }
    'Wake' {
        # HTTP: MacroDroid経由（未設定なら失敗→ADBへ）
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'Wake' } }
        $adbPlan += { Invoke-Adb 'Wake' }
    }
    'Home' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'Home' } }
        $adbPlan += { Invoke-Adb 'Home' }
    }
    'Back' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'Back' } }
        $adbPlan += { Invoke-Adb 'Back' }
    }
    'Recents' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'Recents' } }
        $adbPlan += { Invoke-Adb 'Recents' }
    }
    'ExpandNotifications' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'ExpandNotifications' } }
        $adbPlan += { Invoke-Adb 'ExpandNotifications' }
    }
    'ExpandQuickSettings' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'ExpandQuickSettings' } }
        $adbPlan += { Invoke-Adb 'ExpandQuickSettings' }
    }
    'CollapseStatusBar' {
        $httpPlan += { Invoke-Http 'BroadcastMacro' @{ MacroCmd = 'CollapseStatusBar' } }
        $adbPlan += { Invoke-Adb 'CollapseStatusBar' }
    }
}

$done = $false

if ($adbFirst) {
    if ($adbAllowed) {
        foreach ($step in $adbPlan) {
            if (Invoke-StepAttempt $step) { $done = $true; break }
        }
    }
    if (-not $done -and $httpAllowed) {
        foreach ($step in $httpPlan) {
            if (Invoke-StepAttempt $step) { $done = $true; break }
        }
    }
} else {
    if ($httpAllowed) {
        foreach ($step in $httpPlan) {
            if (Invoke-StepAttempt $step) { $done = $true; break }
        }
    }
    if (-not $done -and $adbAllowed) {
        foreach ($step in $adbPlan) {
            if (Invoke-StepAttempt $step) { $done = $true; break }
        }
    }
}

if (-not $done) {
    Write-Host 'NG: all attempts failed' -ForegroundColor Red
    exit 2
}

Write-Host 'OK' -ForegroundColor Green
