param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'Health',
        'Status',
        'SystemInfo',
        'Resources',
        'OpenUrl',
        'OpenOpenWebUI',
        'OpenApp',
        'BroadcastMacro',
        'MacroCommands'
    )]
    [string]$Action,

    [string]$PixelHost = "",

    [int]$Port = 0,

    [string]$Token = "",

    [string]$Url = "",

    [string]$Package = "",

    [string]$Activity = "",

    [string]$MacroCmd = "",

    [string]$MacroAction = "",

    [string]$ExtrasJson = "",

    [int]$TimeoutSec = 5
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
            $o = Get-Content -Raw -Encoding UTF8 $cfg | ConvertFrom-Json
            if ($o.device_ip) { return [string]$o.device_ip }
        } catch {}
    }

    return '100.84.2.125'
}

function Get-ApiPortDefault {
    if ($env:PIXEL7_API_PORT) {
        $p = 0
        if ([int]::TryParse($env:PIXEL7_API_PORT, [ref]$p) -and $p -gt 0) { return $p }
    }
    return 5122
}

function Get-TokenDefault {
    if ($env:PIXEL7_API_TOKEN) { return $env:PIXEL7_API_TOKEN }
    if ($env:PIXEL7_HTTP_TOKEN) { return $env:PIXEL7_HTTP_TOKEN }
    $tokenFile = Join-Path $PSScriptRoot '.pixel7_api_token.txt'
    if (Test-Path $tokenFile) {
        try {
            $t = (Get-Content -Raw -Encoding UTF8 $tokenFile).Trim()
            if ($t) { return $t }
        } catch {}
    }
    return ''
}

function Get-OpenWebUiUrl {
    if ($env:OPENWEBUI_URL) {
        return $env:OPENWEBUI_URL.TrimEnd('/')
    }

    $statusPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'manaos_integrations\logs\openwebui_tailscale_status.json'
    if (-not (Test-Path $statusPath)) {
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

if ([string]::IsNullOrWhiteSpace($PixelHost)) { $PixelHost = Get-Pixel7IpDefault }
if ($Port -le 0) { $Port = Get-ApiPortDefault }
if ([string]::IsNullOrWhiteSpace($Token)) { $Token = Get-TokenDefault }

$base = if ($env:PIXEL7_API_BASE) { $env:PIXEL7_API_BASE.TrimEnd('/') } else { "http://${PixelHost}:${Port}" }

function Invoke-Pixel7Api([string]$method, [string]$path, $body = $null, [bool]$needsAuth = $true) {
    $uri = $base.TrimEnd('/') + $path

    $headers = @{}
    if ($needsAuth) {
        if ([string]::IsNullOrWhiteSpace($Token)) {
            throw "PIXEL7_API_TOKEN is not set. Set env PIXEL7_API_TOKEN (or pass -Token)."
        }
        $headers['Authorization'] = "Bearer $Token"
    }

    if ($null -eq $body) {
        return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers -TimeoutSec $TimeoutSec
    }

    $json = $body | ConvertTo-Json -Depth 8 -Compress
    return Invoke-RestMethod -Method $method -Uri $uri -Headers $headers -TimeoutSec $TimeoutSec -ContentType 'application/json' -Body $json
}

Write-Host ("=== Pixel7 HTTP Control: {0} ===" -f $Action) -ForegroundColor Cyan
Write-Host ("Base: {0}" -f $base) -ForegroundColor DarkGray

switch ($Action) {
    'Health' {
        $r = Invoke-Pixel7Api 'GET' '/health' $null $false
        $r | ConvertTo-Json -Depth 8
    }
    'Status' {
        $r = Invoke-Pixel7Api 'GET' '/api/status'
        $r | ConvertTo-Json -Depth 8
    }
    'SystemInfo' {
        $r = Invoke-Pixel7Api 'GET' '/api/system/info'
        $r | ConvertTo-Json -Depth 8
    }
    'Resources' {
        $r = Invoke-Pixel7Api 'GET' '/api/system/resources'
        $r | ConvertTo-Json -Depth 8
    }
    'OpenUrl' {
        if ([string]::IsNullOrWhiteSpace($Url)) { throw "-Url is required" }
        $r = Invoke-Pixel7Api 'POST' '/api/open/url' @{ url = $Url }
        if ($null -ne $r.ok -and -not $r.ok) { throw ("OpenUrl failed: {0}" -f ($r.stderr)) }
        $r | ConvertTo-Json -Depth 8
    }
    'OpenOpenWebUI' {
        $u = Get-OpenWebUiUrl
        $r = Invoke-Pixel7Api 'POST' '/api/open/url' @{ url = $u }
        if ($null -ne $r.ok -and -not $r.ok) { throw ("OpenOpenWebUI failed: {0}" -f ($r.stderr)) }
        $r | ConvertTo-Json -Depth 8
    }
    'OpenApp' {
        if ([string]::IsNullOrWhiteSpace($Package)) { throw "-Package is required" }
        $payload = @{ package = $Package }
        if (-not [string]::IsNullOrWhiteSpace($Activity)) { $payload.activity = $Activity }
        $r = Invoke-Pixel7Api 'POST' '/api/open/app' $payload
        if ($null -ne $r.ok -and -not $r.ok) { throw ("OpenApp failed: {0}" -f ($r.stderr)) }
        $r | ConvertTo-Json -Depth 8
    }
    'BroadcastMacro' {
        if ([string]::IsNullOrWhiteSpace($MacroCmd)) { throw "-MacroCmd is required" }
        $payload = @{ cmd = $MacroCmd }
        if (-not [string]::IsNullOrWhiteSpace($MacroAction)) { $payload.action = $MacroAction }
        if (-not [string]::IsNullOrWhiteSpace($ExtrasJson)) {
            try {
                $payload.extras = ($ExtrasJson | ConvertFrom-Json)
            } catch {
                throw "-ExtrasJson must be valid JSON (object)."
            }
        }
        $r = Invoke-Pixel7Api 'POST' '/api/macro/broadcast' $payload
        if ($null -ne $r.ok -and -not $r.ok) { throw ("BroadcastMacro failed: {0}" -f ($r.stderr)) }
        $r | ConvertTo-Json -Depth 8
    }
    'MacroCommands' {
        $r = Invoke-Pixel7Api 'GET' '/api/macro/commands'
        $r | ConvertTo-Json -Depth 8
    }
}
