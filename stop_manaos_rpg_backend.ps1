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
foreach ($processId in $pids) {
    try {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -eq $proc) {
            Write-Host "[INFO] pid=$processId already exited" -ForegroundColor DarkYellow
            continue
        }
        Stop-Process -Id $processId -Force -ErrorAction Stop
        Write-Host "[OK] Stopped process pid=$processId on port $Port" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Failed to stop pid=${processId}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

exit 0
