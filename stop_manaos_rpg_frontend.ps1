param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) {
    Write-Host "[INFO] No frontend listener found on port $Port" -ForegroundColor Yellow
    exit 0
}

$pids = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($processId in $pids) {
    try {
        Stop-Process -Id $processId -Force -ErrorAction Stop
        Write-Host "[OK] Stopped process pid=$processId on port $Port" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Failed to stop pid=${processId}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

exit 0
