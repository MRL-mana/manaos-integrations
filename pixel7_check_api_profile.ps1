param(
    [ValidateSet('any','core','full')]
    [string]$Require = 'any',
    [string]$BaseUrl = '',
    [int]$TimeoutSec = 5,
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'

function Get-Pixel7IpDefault {
    if ($env:PIXEL7_API_HOST) { return $env:PIXEL7_API_HOST }
    if ($env:PIXEL7_TAILSCALE_IP) { return $env:PIXEL7_TAILSCALE_IP }
    if ($env:PIXEL7_IP) { return $env:PIXEL7_IP }

    $cfg = Join-Path $PSScriptRoot 'adb_automation_config.json'
    if (-not (Test-Path $cfg)) {
        $cfg = Join-Path (Split-Path $PSScriptRoot -Parent) 'manaos_integrations\adb_automation_config.json'
    }
    if (Test-Path $cfg) {
        try {
            $obj = Get-Content -Raw -Encoding UTF8 $cfg | ConvertFrom-Json
            if ($obj.device_ip) { return [string]$obj.device_ip }
        } catch {}
    }

    return '100.84.2.125'
}

function Get-ApiPortDefault {
    if ($env:PIXEL7_API_PORT) {
        $portNum = 0
        if ([int]::TryParse($env:PIXEL7_API_PORT, [ref]$portNum) -and $portNum -gt 0) { return $portNum }
    }
    return 5122
}

function Resolve-BaseUrl {
    param([string]$Value)

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $Value.TrimEnd('/')
    }

    if ($env:PIXEL7_API_BASE) {
        return $env:PIXEL7_API_BASE.TrimEnd('/')
    }

    $pixelHost = Get-Pixel7IpDefault
    $port = Get-ApiPortDefault
    return ("http://{0}:{1}" -f $pixelHost, $port)
}

$base = Resolve-BaseUrl -Value $BaseUrl
$uri = $base + '/'

try {
    $root = Invoke-RestMethod -Method GET -Uri $uri -TimeoutSec $TimeoutSec
} catch {
    Write-Error ("failed to reach Pixel7 API root: {0}" -f $_.Exception.Message)
    exit 1
}

$profile = [string]$root.api_profile
$result = [ordered]@{
    ok = $true
    base_url = $base
    require = $Require
    api_profile = $profile
    status = [string]$root.status
    service = [string]$root.service
}

if ([string]::IsNullOrWhiteSpace($profile)) {
    if ($Require -ne 'any') {
        $result.ok = $false
        $result.reason = 'api_profile missing from root response (old gateway? re-deploy/start latest gateway)'
    } else {
        $result.reason = 'api_profile missing (old gateway?) -> re-deploy/start latest gateway to enable core/full profile checks'
    }
} elseif ($Require -ne 'any' -and $profile -ne $Require) {
    $result.ok = $false
    $result.reason = ("profile mismatch (need={0}, got={1})" -f $Require, $profile)
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
} else {
    $profileText = if ([string]::IsNullOrWhiteSpace($profile)) { 'unknown' } else { $profile }
    Write-Host ("Pixel7 API profile: {0} (require={1}) @ {2}" -f $profileText, $Require, $base) -ForegroundColor Cyan
    if ($result.reason) {
        $color = if ($result.ok) { 'Yellow' } else { 'Red' }
        Write-Host $result.reason -ForegroundColor $color
    }
}

if (-not $result.ok) {
    exit 2
}

exit 0
