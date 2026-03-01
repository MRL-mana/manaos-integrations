param(
    [switch]$Recover,
    [string]$Distro = "Ubuntu-22.04",
    [string]$LogDir = "c:\Users\mana4\Desktop\manaos_integrations\logs",
    [int]$TimeoutSec = 20
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line
}

function Get-DockerCliPath {
    $candidates = @(
        "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        "C:\Program Files\Docker\Docker\Docker\resources\bin\docker.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    try {
        $cmd = Get-Command docker -ErrorAction Stop
        if ($cmd -and $cmd.Source) {
            return $cmd.Source
        }
    }
    catch {}

    return $null
}

function Test-DockerServer {
    param(
        [int]$CommandTimeoutSec = 6
    )

    if ([string]::IsNullOrWhiteSpace($script:DockerCliPath)) {
        return $false
    }

    try {
        $job = Start-Job -ScriptBlock {
            param($DockerCli)
            & $DockerCli version --format '{{.Server.Version}}' 2>$null | Out-Null
            return $LASTEXITCODE
        } -ArgumentList $script:DockerCliPath

        $completed = Wait-Job -Job $job -Timeout $CommandTimeoutSec
        if (-not $completed) {
            Stop-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
            return $false
        }

        $code = Receive-Job -Job $job -Keep
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
        return [int]$code -eq 0
    }
    catch {
        return $false
    }
}

function Test-WslDistroRunning {
    param(
        [string]$Name,
        [int]$CommandTimeoutSec = 8
    )

    try {
        $job = Start-Job -ScriptBlock {
            param($DistroName)
            wsl -d $DistroName --exec /bin/true 2>$null | Out-Null
            return $LASTEXITCODE
        } -ArgumentList $Name

        $completed = Wait-Job -Job $job -Timeout $CommandTimeoutSec
        if (-not $completed) {
            Stop-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
            return $false
        }

        $code = Receive-Job -Job $job -Keep
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
        return [int]$code -eq 0
    }
    catch {}
    return $false
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$script:LogFile = Join-Path $LogDir ("wsl_docker_health_" + (Get-Date -Format "yyyy-MM-dd") + ".log")
$script:DockerCliPath = Get-DockerCliPath

Write-Log "=== WSL/Docker health check start ==="
Write-Log "Distro=$Distro Recover=$Recover"
if ([string]::IsNullOrWhiteSpace($script:DockerCliPath)) {
    Write-Log "Docker CLI path not found" "WARN"
}
else {
    Write-Log "Docker CLI path: $script:DockerCliPath"
}

$wslRunning = Test-WslDistroRunning -Name $Distro
$dockerOk = Test-DockerServer

Write-Log "WSL distro running: $wslRunning"
Write-Log "Docker server reachable: $dockerOk"

if ($dockerOk -and $wslRunning) {
    Write-Log "Healthy"
    exit 0
}

Write-Log "Unhealthy detected" "WARN"

if (-not $Recover) {
    Write-Log "Recovery disabled. Exiting with code 1" "WARN"
    exit 1
}

Write-Log "Recovery start: wsl --shutdown"
try {
    wsl --shutdown | Out-Null
}
catch {
    Write-Log "wsl --shutdown failed: $($_.Exception.Message)" "ERROR"
}

Start-Sleep -Seconds 3

Write-Log "Recovery step: restart Docker Desktop process"
try {
    Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process -Name "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
catch {
    Write-Log "Docker process stop warning: $($_.Exception.Message)" "WARN"
}

$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerExe) {
    Start-Process -FilePath $dockerExe | Out-Null
    Write-Log "Docker Desktop start triggered"
}
else {
    Write-Log "Docker Desktop executable not found: $dockerExe" "ERROR"
}

Write-Log "Recovery step: ensure WSL distro start"
try {
    wsl -d $Distro --exec /bin/true | Out-Null
    Write-Log "WSL start triggered for distro: $Distro"
}
catch {
    Write-Log "WSL start warning: $($_.Exception.Message)" "WARN"
}

$deadline = (Get-Date).AddSeconds($TimeoutSec)
$recovered = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    $dockerRecovered = Test-DockerServer
    $wslRecovered = Test-WslDistroRunning -Name $Distro
    if ($dockerRecovered -and $wslRecovered) {
        $recovered = $true
        break
    }
}

if ($recovered) {
    Write-Log "Recovery succeeded (docker+wsl)"
    exit 0
}

Write-Log "Recovery failed (timeout=${TimeoutSec}s)" "ERROR"
exit 2
