param(
	[switch]$Lan,
	[switch]$EnableActions,
	[int]$ApiPort = 9510,
	[int]$UiPort = 5173
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Test-Listening([int]$Port) {
	try {
		$c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
		return [bool]$c
	} catch {
		return $false
	}
}

$backendArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', (Join-Path $PSScriptRoot 'run_backend.ps1'), '-Port', "$ApiPort")
if ($Lan.IsPresent) { $backendArgs += '-Lan' }
if ($EnableActions.IsPresent) { $backendArgs += '-EnableActions' }

$frontendArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', (Join-Path $PSScriptRoot 'run_frontend.ps1'), '-Port', "$UiPort")
if ($Lan.IsPresent) { $frontendArgs += '-Lan' }

if (-not (Test-Listening -Port $ApiPort)) {
	$backendLog = Join-Path $logs 'backend.out.log'
	$backendErr = Join-Path $logs 'backend.err.log'
	Write-Host "[manaos-rpg] Starting backend in background (port=$ApiPort)" -ForegroundColor Cyan
	Start-Process -FilePath 'pwsh' -ArgumentList $backendArgs -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr | Out-Null
} else {
	Write-Host "[manaos-rpg] Backend already listening on port $ApiPort" -ForegroundColor DarkGreen
}

if (-not (Test-Listening -Port $UiPort)) {
	$frontendLog = Join-Path $logs 'frontend.out.log'
	$frontendErr = Join-Path $logs 'frontend.err.log'
	Write-Host "[manaos-rpg] Starting frontend in background (port=$UiPort)" -ForegroundColor Cyan
	Start-Process -FilePath 'pwsh' -ArgumentList $frontendArgs -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr | Out-Null
} else {
	Write-Host "[manaos-rpg] Frontend already listening on port $UiPort" -ForegroundColor DarkGreen
}

Write-Host "[manaos-rpg] Access:" -ForegroundColor Green
if ($Lan.IsPresent) {
	Write-Host "  UI:  http://<this-pc-ip>:$UiPort/" -ForegroundColor Green
	Write-Host "  API: http://<this-pc-ip>:$ApiPort/health" -ForegroundColor Green
} else {
	Write-Host "  UI:  http://127.0.0.1:$UiPort/" -ForegroundColor Green
	Write-Host "  API: http://127.0.0.1:$ApiPort/health" -ForegroundColor Green
}
