param(
  [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\")).Path,
  [string]$ComposeFile = "",
  [int]$IntervalSec = 20,
  [switch]$RemoveOrphans,
  [int]$DockerReadyTimeoutSec = 90
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$logDir = Join-Path $WorkingDir "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir "manaos_docker_stack_watcher.log"

function Write-Log {
  param([string]$Message, [string]$Level = "INFO")
  $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  $line = "[$ts][$Level] $Message"
  try { Add-Content -Path $logFile -Value $line } catch { }
  Write-Host $line
}

trap {
  try { Write-Log -Level "ERROR" -Message ("Terminating error: " + ($_.ToString())) } catch { }
  exit 1
}

# Prevent duplicate instances (e.g. Run key + manual start)
$mutexName = "Global\ManaOSDockerStackWatcher"
$mutex = New-Object System.Threading.Mutex($false, $mutexName)
if (-not $mutex.WaitOne(0)) {
  Write-Host "[ManaOS] Another docker stack watcher is already running ($mutexName). Exiting." -ForegroundColor Yellow
  exit 0
}

function Test-DockerReady {
  try {
    docker info 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

function Wait-DockerReady {
  param([int]$TimeoutSec)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-DockerReady) { return }
    Start-Sleep -Seconds 3
  }
  throw "Docker is not ready after ${TimeoutSec}s. Is Docker Desktop running?"
}

function Get-UnifiedApiPort {
  if ($env:UNIFIED_API_PORT) {
    try { return [int]$env:UNIFIED_API_PORT } catch { }
  }
  if ($env:PORT) {
    try { return [int]$env:PORT } catch { }
  }
  return 9502
}

if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
  $ComposeFile = Join-Path $WorkingDir "docker-compose.yml"
}

if (!(Test-Path $ComposeFile)) {
  throw "Compose file not found: $ComposeFile"
}

Write-Log "WorkingDir: $WorkingDir"
Write-Log "ComposeFile: $ComposeFile"
Write-Log "IntervalSec: $IntervalSec"
Write-Log "Watcher mutex: $mutexName" "DEBUG"

Set-Location $WorkingDir

Wait-DockerReady -TimeoutSec $DockerReadyTimeoutSec

$composeArgs = @("compose", "-f", $ComposeFile, "up", "-d")
if ($RemoveOrphans) {
  $composeArgs += "--remove-orphans"
}

Write-Log "docker $($composeArgs -join ' ')"
& docker @composeArgs

$unifiedApiPort = Get-UnifiedApiPort
$healthUrl = "http://127.0.0.1:${unifiedApiPort}/health"

Write-Log "Health URL: $healthUrl"

while ($true) {
  try {
    $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($resp.StatusCode -ne 200) {
      throw "health status code: $($resp.StatusCode)"
    }
  }
  catch {
    Write-Log "Unified API health check failed: $($_.Exception.Message)" "WARN"
    Write-Log "Attempting to (re)apply docker compose up -d..." "WARN"
    try {
      & docker @composeArgs | Out-Null
    } catch {
      Write-Log "docker compose up failed: $($_.Exception.Message)" "WARN"
    }
  }

  Start-Sleep -Seconds $IntervalSec
}
