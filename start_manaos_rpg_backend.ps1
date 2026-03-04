param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 9510,
    [int]$StartupTimeoutSec = 20,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "manaos-rpg\backend"
$stopScript = Join-Path $scriptDir "stop_manaos_rpg_backend.ps1"

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}
if (-not (Test-Path $stopScript)) {
    throw "Stop script not found: $stopScript"
}

function Resolve-PythonExe {
    param([string]$ScriptRoot, [string]$Provided)

    if (-not [string]::IsNullOrWhiteSpace($Provided) -and (Test-Path $Provided)) {
        return $Provided
    }

    $candidates = @(
        (Join-Path $ScriptRoot ".venv\Scripts\python.exe"),
        (Join-Path (Split-Path $ScriptRoot -Parent) ".venv\Scripts\python.exe"),
        (Join-Path (Split-Path $ScriptRoot -Parent) ".venv310\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return "python"
}

function Get-HealthCode {
    param([string]$HostName, [int]$PortNumber)

    try {
        $code = & curl.exe -s -o NUL -w "%{http_code}" --connect-timeout 2 --max-time 4 "http://${HostName}:${PortNumber}/health"
        if ($LASTEXITCODE -ne 0) {
            return "000"
        }
        return [string]$code
    }
    catch {
        return "000"
    }
}

function Get-TailscaleIPv4 {
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*Tailscale*' -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty IPAddress -First 1
        if (-not [string]::IsNullOrWhiteSpace($ip)) {
            return [string]$ip
        }
    }
    catch {
    }
    return ""
}

function Ensure-CorsOriginsForRemote {
    param([string]$HostName, [int]$PortNumber)

    if ($HostName -eq "127.0.0.1" -or $HostName -eq "localhost") {
        return
    }
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_CORS_ORIGINS)) {
        return
    }

    $origins = New-Object System.Collections.Generic.List[string]
    $origins.Add("http://localhost:5173")
    $origins.Add("http://127.0.0.1:5173")
    $origins.Add("http://$env:COMPUTERNAME:5173")

    try {
        $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -and $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } |
            Select-Object -ExpandProperty IPAddress -Unique
        foreach ($ip in $ips) {
            $origins.Add("http://$ip:5173")
        }
    }
    catch {
    }

    $tailscaleIp = Get-TailscaleIPv4
    if (-not [string]::IsNullOrWhiteSpace($tailscaleIp)) {
        $origins.Add("http://$tailscaleIp:5173")
    }

    $env:MANAOS_CORS_ORIGINS = (($origins | Select-Object -Unique) -join ',')
}

function Resolve-ProbeHost {
    param([string]$HostName)

    if ($HostName -eq "0.0.0.0" -or $HostName -eq "::") {
        return "127.0.0.1"
    }
    return $HostName
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$probeHost = Resolve-ProbeHost -HostName $ListenHost
if ($null -ne $listener) {
    $healthCode = Get-HealthCode -HostName $probeHost -PortNumber $Port
    if ($healthCode -eq "200") {
        Write-Host "[OK] Backend already running on ${ListenHost}:${Port} (pid=$($listener.OwningProcess))" -ForegroundColor Green
        exit 0
    }
    Write-Host "[WARN] Port $Port is in use but /health is not 200 (code=$healthCode), trying recovery stop/start" -ForegroundColor Yellow
    & pwsh -NoProfile -ExecutionPolicy Bypass -File $stopScript -Port $Port -ForceAllListeners
    Start-Sleep -Milliseconds 600
}

$resolvedPython = Resolve-PythonExe -ScriptRoot $scriptDir -Provided $PythonExe
Ensure-CorsOriginsForRemote -HostName $ListenHost -PortNumber $Port
$args = @("-m", "uvicorn", "app:app", "--host", $ListenHost, "--port", "$Port")
$proc = Start-Process -FilePath $resolvedPython -ArgumentList $args -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
$started = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 700
    $healthCode = Get-HealthCode -HostName $probeHost -PortNumber $Port
    if ($healthCode -eq "200") {
        $started = $true
        break
    }
}

if ($started) {
    Write-Host "[OK] Backend started on ${ListenHost}:${Port} (pid=$($proc.Id))" -ForegroundColor Green
    exit 0
}

try {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
catch {
}

Write-Host "[ALERT] Backend startup timed out on ${ListenHost}:${Port}" -ForegroundColor Red
exit 1
