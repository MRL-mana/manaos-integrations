param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 5173,
    [switch]$AsJson,
    [switch]$RequirePass
)

$ErrorActionPreference = "Stop"

function Get-HttpCode {
    param([string]$HostName, [int]$PortNumber)

    try {
        $code = & curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 2 --max-time 4 "http://${HostName}:${PortNumber}"
        if ($LASTEXITCODE -ne 0) {
            return "000"
        }
        return [string]$code
    }
    catch {
        return "000"
    }
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$httpCode = Get-HttpCode -HostName $BindAddress -PortNumber $Port

$payload = [ordered]@{
    host = $BindAddress
    port = $Port
    listening = ($null -ne $listener)
    pid = if ($null -ne $listener) { [int]$listener.OwningProcess } else { -1 }
    http_code = $httpCode
    ok_reason = "not_listening"
}

if ($payload.listening -and ($httpCode -match '^(200|304)$')) {
    $payload.ok_reason = "healthy"
}
elseif ($payload.listening) {
    $payload.ok_reason = "http_not_ok"
}

$pass = ($payload.listening -and ($httpCode -match '^(200|304)$'))

if ($AsJson) {
    $payload.require_pass = [bool]$RequirePass
    $payload.pass = $pass
    Write-Output ($payload | ConvertTo-Json -Depth 6)
    if ($RequirePass.IsPresent -and -not $pass) {
        exit 1
    }
    exit 0
}

Write-Host "=== ManaOS RPG Frontend Status ===" -ForegroundColor Cyan
Write-Host "host: $BindAddress" -ForegroundColor Gray
Write-Host "port: $Port" -ForegroundColor Gray
Write-Host "listening: $($payload.listening)" -ForegroundColor Gray
Write-Host "pid: $($payload.pid)" -ForegroundColor Gray
Write-Host "http_code: $httpCode" -ForegroundColor Gray
Write-Host "ok_reason: $($payload.ok_reason)" -ForegroundColor Gray
Write-Host "pass: $pass" -ForegroundColor Gray

if ($RequirePass.IsPresent -and -not $pass) {
    Write-Host "[ALERT] RPG frontend status is not pass" -ForegroundColor Red
    exit 1
}

exit 0
