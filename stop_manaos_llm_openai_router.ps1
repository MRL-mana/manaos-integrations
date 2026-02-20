param()

$ErrorActionPreference = "Stop"

$patterns = @(
    "*start_manaos_llm_openai_router.ps1*",
    "*manaos_llm_routing_api.py*"
)

$targets = @()

$targets += Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like $patterns[0] }

$targets += Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like $patterns[1] }

$targets += Get-CimInstance Win32_Process -Filter "Name='py.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like $patterns[1] }

if (-not $targets -or $targets.Count -eq 0) {
    Write-Host "[OK] No router process found" -ForegroundColor Green
    exit 0
}

$stopped = 0
foreach ($proc in $targets | Sort-Object ProcessId -Unique) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        $stopped++
    }
    catch {
        Write-Host ("[WARN] Failed to stop PID {0}" -f $proc.ProcessId) -ForegroundColor Yellow
    }
}

Write-Host ("[OK] Stopped router-related processes: {0}" -f $stopped) -ForegroundColor Green
exit 0
