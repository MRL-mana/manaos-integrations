$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'

Set-Location $backend

Write-Host "[manaos-rpg] Installing backend deps..." -ForegroundColor Cyan
py -3.10 -m pip install -r .\requirements.txt

Write-Host "[manaos-rpg] Starting API on http://127.0.0.1:9510" -ForegroundColor Green
py -3.10 -m uvicorn app:app --host 127.0.0.1 --port 9510
