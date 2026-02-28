param(
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 9510,
    [int]$StartupTimeoutSec = 20,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "manaos-rpg\backend"

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
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

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $listener) {
    $healthCode = Get-HealthCode -HostName $ListenHost -PortNumber $Port
    if ($healthCode -eq "200") {
        Write-Host "[OK] Backend already running on ${ListenHost}:${Port} (pid=$($listener.OwningProcess))" -ForegroundColor Green
        exit 0
    }
    Write-Host "[WARN] Port $Port is in use but /health is not 200 (code=$healthCode)" -ForegroundColor Yellow
    exit 1
}

$resolvedPython = Resolve-PythonExe -ScriptRoot $scriptDir -Provided $PythonExe
$args = @("-m", "uvicorn", "app:app", "--host", $ListenHost, "--port", "$Port")
$proc = Start-Process -FilePath $resolvedPython -ArgumentList $args -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
$started = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 700
    $healthCode = Get-HealthCode -HostName $ListenHost -PortNumber $Port
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
