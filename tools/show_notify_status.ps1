param(
    [int]$TailLines = 100
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

if ($TailLines -lt 1) {
    throw "TailLines must be >= 1"
}

$logs = @(
    @{ Name = "file_secretary_fail_check"; Path = Join-Path $repo "logs\file_secretary_fail_check.log" },
    @{ Name = "dashboard_alert"; Path = Join-Path $repo "logs\dashboard_alert.log" }
)

foreach ($log in $logs) {
    Write-Host ("=== {0} ===" -f $log.Name) -ForegroundColor Cyan

    if (-not (Test-Path $log.Path)) {
        Write-Host "(log missing)" -ForegroundColor Yellow
        continue
    }

    $matches = Get-Content $log.Path -Tail $TailLines | Where-Object { $_ -match "notify=" }

    if (-not $matches -or $matches.Count -eq 0) {
        Write-Host "(no notify entries)" -ForegroundColor DarkGray
        continue
    }

    $matches | Select-Object -Last 10 | ForEach-Object { Write-Host $_ }
}
