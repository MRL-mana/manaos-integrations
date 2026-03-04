param(
    [string]$BindAddress = "127.0.0.1",
    [int]$Port = 5173,
    [int]$StartupTimeoutSec = 25,
    [ValidateSet('dev','preview')]
    [string]$ServeMode = 'dev'
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $scriptDir "manaos-rpg\frontend"

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

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

function Resolve-ProbeHost {
    param([string]$HostName)

    if ($HostName -eq "0.0.0.0" -or $HostName -eq "::") {
        return "127.0.0.1"
    }
    return $HostName
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$probeHost = Resolve-ProbeHost -HostName $BindAddress
if ($null -ne $listener) {
    $httpCode = Get-HttpCode -HostName $probeHost -PortNumber $Port
    if ($httpCode -match '^(200|304)$') {
        Write-Host "[OK] Frontend already running on ${BindAddress}:${Port} (pid=$($listener.OwningProcess))" -ForegroundColor Green
        exit 0
    }
    Write-Host "[WARN] Port $Port is in use but HTTP probe failed (code=$httpCode)" -ForegroundColor Yellow
    exit 1
}

if ($ServeMode -eq 'preview') {
    $buildArgs = @('/c', 'npm', 'run', 'build')
    $buildProc = Start-Process -FilePath 'cmd.exe' -ArgumentList $buildArgs -WorkingDirectory $frontendDir -PassThru -Wait -WindowStyle Hidden
    if ($buildProc.ExitCode -ne 0) {
        Write-Host "[ALERT] Frontend build failed (exit=$($buildProc.ExitCode))" -ForegroundColor Red
        exit 1
    }
    $cmdArgs = @('/c', 'npm', 'run', 'preview', '--', '--host', $BindAddress, '--port', "$Port", '--strictPort')
}
else {
    $cmdArgs = @('/c', 'npm', 'run', 'dev', '--', '--host', $BindAddress, '--port', "$Port", '--strictPort')
}

$proc = Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
$started = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 700
    $httpCode = Get-HttpCode -HostName $probeHost -PortNumber $Port
    if ($httpCode -match '^(200|304)$') {
        $started = $true
        break
    }
}

if ($started) {
    Write-Host "[OK] Frontend started on ${BindAddress}:${Port} (pid=$($proc.Id), mode=$ServeMode)" -ForegroundColor Green
    exit 0
}

try {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
    }
}
catch {
}

Write-Host "[ALERT] Frontend startup timed out on ${BindAddress}:${Port}" -ForegroundColor Red
exit 1
