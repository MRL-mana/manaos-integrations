param(
	[string]$BindHost = '127.0.0.1',
	[int]$Port = 5173,
	[switch]$Lan
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'

Set-Location $frontend

Write-Host "[manaos-rpg] Installing frontend deps..." -ForegroundColor Cyan
npm install

if ($Lan.IsPresent) {
	$BindHost = '0.0.0.0'
}

Write-Host "[manaos-rpg] Starting UI on http://${BindHost}:${Port}" -ForegroundColor Green
npm run dev -- --host $BindHost --port $Port
