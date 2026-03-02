# Pixel7 MacroDroid sender (HTTP first, optional ADB fallback)

param(
    [Parameter(Mandatory = $true)]
    [string]$MacroCmd,

    [string]$ExtrasJson = "{}",

    [ValidateSet('HTTPFirst', 'HTTPOnly', 'ADBOnly')]
    [string]$Mode = 'HTTPFirst',

    [int]$TimeoutSec = 5,

    [string]$DeviceSerial = ""
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($MacroCmd)) {
    throw "-MacroCmd is required"
}

$httpCtl = Join-Path $PSScriptRoot 'pixel7_http_control.ps1'
$adbCtl = Join-Path $PSScriptRoot 'pixel7_remote_control.ps1'

if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }
if (-not (Test-Path $adbCtl)) { throw "not found: $adbCtl" }

function Resolve-HttpBaseUrl {
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

function Invoke-HttpAttempt {
    try {
        $pwshArgList = @(
            '-NoProfile','-ExecutionPolicy','Bypass','-File', $httpCtl,
            '-Action','BroadcastMacro',
            '-MacroCmd', $MacroCmd,
            '-ExtrasJson', $ExtrasJson,
            '-TimeoutSec', [string]$TimeoutSec
        )
        $out = & powershell @pwshArgList 2>&1 | Out-String
        if ($out) { $out.TrimEnd() | Out-Host }
        return $true
    } catch {
        Write-Host ("[HTTP NG] {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        return $false
    }
}

function Invoke-AdbAttempt {
    $map = @{
        'Wake' = 'Wake'
        'Home' = 'Home'
        'Back' = 'Back'
        'Recents' = 'Recents'
        'ExpandNotifications' = 'ExpandNotifications'
        'ExpandQuickSettings' = 'ExpandQuickSettings'
        'CollapseStatusBar' = 'CollapseStatusBar'
        'OpenHttpShortcuts' = 'OpenHttpShortcuts'
        'OpenOpenWebUI' = 'OpenOpenWebUI'
        'OpenTermux' = 'OpenTermux'
    }

    if (-not $map.ContainsKey($MacroCmd)) {
        Write-Host ("[ADB SKIP] no fallback mapping for cmd='{0}'" -f $MacroCmd) -ForegroundColor DarkGray
        return $false
    }

    $adbAction = $map[$MacroCmd]

    try {
        $pwshArgList = @(
            '-NoProfile','-ExecutionPolicy','Bypass','-File', $adbCtl,
            '-Action', $adbAction
        )
        if (-not [string]::IsNullOrWhiteSpace($DeviceSerial)) {
            $pwshArgList += @('-DeviceSerial', $DeviceSerial)
        }

        $out = & powershell @pwshArgList 2>&1 | Out-String
        if ($out) { $out.TrimEnd() | Out-Host }
        return $true
    } catch {
        Write-Host ("[ADB NG] {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        return $false
    }
}

Write-Host ("=== Pixel7 Macro Send Auto: cmd={0} mode={1} ===" -f $MacroCmd, $Mode) -ForegroundColor Cyan

$ok = $false
$preferAdb = $false

if ($Mode -eq 'HTTPFirst') {
    $profile = Get-Pixel7ApiProfile
    if ($profile -and $profile -ne 'full') {
        Write-Host ("[INFO] HTTP skipped: PIXEL7_API_PROFILE={0}. trying ADB fallback first." -f $profile) -ForegroundColor Yellow
        $preferAdb = $true
    }
}

if ($Mode -eq 'HTTPOnly') {
    $ok = Invoke-HttpAttempt
} elseif ($Mode -eq 'ADBOnly') {
    $ok = Invoke-AdbAttempt
} else {
    if ($preferAdb) {
        $ok = Invoke-AdbAttempt
        if (-not $ok) {
            Write-Host '[INFO] ADB failed; retrying HTTP' -ForegroundColor Gray
            $ok = Invoke-HttpAttempt
        }
    } else {
        $ok = Invoke-HttpAttempt
        if (-not $ok) {
            Write-Host '[INFO] falling back to ADB (if supported)' -ForegroundColor Gray
            $ok = Invoke-AdbAttempt
        }
    }
}

if (-not $ok) {
    Write-Host 'NG' -ForegroundColor Red
    exit 2
}

Write-Host 'OK' -ForegroundColor Green
