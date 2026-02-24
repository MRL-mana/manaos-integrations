$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'

Set-Location $frontend

Write-Host "[manaos-rpg] Installing frontend deps..." -ForegroundColor Cyan
npm install

Write-Host "[manaos-rpg] Starting UI on http://127.0.0.1:5173" -ForegroundColor Green
npm run dev -- --host 127.0.0.1 --port 5173
