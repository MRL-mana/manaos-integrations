param(
    [switch]$KillScrcpy
)

$ErrorActionPreference = 'Stop'

$pidFile = Join-Path $PSScriptRoot '.pixel7_scrcpy_watch.pid'

function Stop-WatchByCommandLine {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -match 'pixel7_scrcpy_watch\.ps1' }
        foreach ($p in $procs) {
            try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
        }
    } catch {}
}

if (Test-Path $pidFile) {
    try {
        $pid = (Get-Content -Raw -ErrorAction SilentlyContinue $pidFile).Trim()
        if ($pid -match '^\d+$') {
            Stop-Process -Id ([int]$pid) -Force -ErrorAction SilentlyContinue
        }
    } catch {}

    try { Remove-Item $pidFile -Force -ErrorAction SilentlyContinue } catch {}
}

# 二重起動やpidfile不整合に備えて、コマンドラインからも全停止
Stop-WatchByCommandLine

if ($KillScrcpy) {
    Stop-Process -Name scrcpy -Force -ErrorAction SilentlyContinue
}

Write-Host 'OK' -ForegroundColor Green
