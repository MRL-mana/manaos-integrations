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

function Invoke-Http([string]$httpAction, [hashtable]$extraArgs = @{}) {
    if (-not (Test-Path $http)) { throw "pixel7_http_control.ps1 not found: $http" }

    $pwshArgList = @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File', $http,
        '-Action', $httpAction,
        '-TimeoutSec', [string]$TimeoutSec
    )

    foreach ($k in $extraArgs.Keys) {
        $pwshArgList += @("-$k", [string]$extraArgs[$k])
    }

    $out = & powershell @pwshArgList 2>&1 | Out-String
    return $out
}

function Invoke-Adb([string]$adbAction, [hashtable]$extraArgs = @{}) {
    if (-not (Test-Path $adb)) { throw "pixel7_remote_control.ps1 not found: $adb" }

    $pwshArgList = @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File', $adb,
        '-Action', $adbAction
    )

    if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
        $pwshArgList += @('-DeviceSerial', $DeviceSerial)
    }

    foreach ($k in $extraArgs.Keys) {
        $pwshArgList += @("-$k", [string]$extraArgs[$k])
    }

    $out = & powershell @pwshArgList 2>&1 | Out-String
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

Write-Host ("=== Pixel7 Control (HTTP→ADB): {0} mode={1} ===" -f $Action, $Mode) -ForegroundColor Cyan

$adbFirst = $Mode -in @('ADBFirst','ADBOnly')
$httpAllowed = $Mode -notin @('ADBOnly')
$adbAllowed = $Mode -notin @('HTTPOnly')

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
