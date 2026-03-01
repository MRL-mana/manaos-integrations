param(
    [ValidateSet('any','core','full')]
    [string]$Require = 'any',
    [string]$BaseUrl = '',
    [int]$TimeoutSec = 5,
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'

function Resolve-BaseUrl {
    param([string]$Value)

    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $Value.TrimEnd('/')
    }

    if ($env:PIXEL7_API_BASE) {
        return $env:PIXEL7_API_BASE.TrimEnd('/')
    }

    $pixelHost = if ($env:PIXEL7_API_HOST) { $env:PIXEL7_API_HOST } elseif ($env:PIXEL7_TAILSCALE_IP) { $env:PIXEL7_TAILSCALE_IP } else { '127.0.0.1' }
    $port = if ($env:PIXEL7_API_PORT) { $env:PIXEL7_API_PORT } else { '5122' }
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
        $result.reason = 'api_profile missing from root response'
    } else {
        $result.reason = 'api_profile missing (old gateway?)'
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
