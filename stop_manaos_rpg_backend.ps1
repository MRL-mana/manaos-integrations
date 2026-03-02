param(
    [int]$Port = 9510,
    [switch]$ForceAllListeners
)

$ErrorActionPreference = "Stop"

$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) {
    Write-Host "[INFO] No backend listener found on port $Port" -ForegroundColor Yellow
    exit 0
}

$pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
$stoppedAny = $false
foreach ($processId in $pids) {
    try {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $proc) {
            Write-Host "[INFO] pid=$processId already exited" -ForegroundColor DarkYellow
            continue
        }

        $isBackendLike = $false
        $commandLine = ""
        try {
            $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction Stop
            $commandLine = [string]$wmi.CommandLine
            $cmdLower = $commandLine.ToLowerInvariant()
            $isBackendLike = ($cmdLower.Contains("uvicorn") -and $cmdLower.Contains("app:app"))
        }
        catch {
        }

        if (-not $ForceAllListeners.IsPresent -and -not $isBackendLike) {
            Write-Host "[INFO] Skip non-backend listener pid=$processId on port $Port (use -ForceAllListeners to stop anyway)" -ForegroundColor DarkYellow
            if (-not [string]::IsNullOrWhiteSpace($commandLine)) {
                Write-Host ("  cmd: {0}" -f $commandLine) -ForegroundColor DarkGray
            }
            continue
        }

        Stop-Process -Id $processId -Force -ErrorAction Stop
        Write-Host "[OK] Stopped process pid=$processId on port $Port" -ForegroundColor Green
        $stoppedAny = $true
    }
    catch {
        Write-Host "[WARN] Failed to stop pid=${processId}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

if (-not $stoppedAny -and -not $ForceAllListeners.IsPresent) {
    Write-Host "[INFO] No backend-like listener process was stopped on port $Port" -ForegroundColor DarkYellow
}

exit 0
