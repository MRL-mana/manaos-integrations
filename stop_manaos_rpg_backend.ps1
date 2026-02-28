param(
    [int]$Port = 9510
)

$ErrorActionPreference = "Stop"

$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) {
    Write-Host "[INFO] No backend listener found on port $Port" -ForegroundColor Yellow
    exit 0
}

$pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($pid in $pids) {
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Write-Host "[OK] Stopped process pid=$pid on port $Port" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Failed to stop pid=${pid}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

exit 0
