param(
	[string]$BindHost = '127.0.0.1',
	[int]$Port = 9510,
	[switch]$ForceKill,
	[switch]$EnableActions
)

$ErrorActionPreference = 'Stop'

function Get-ProcessCommandLine([int]$ProcessId) {
	try {
		$p = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
		return [string]$p.CommandLine
	} catch {
		return ''
	}
}

function Stop-ListenerOnPort([int]$PortToStop, [switch]$ForceKillListener) {
	$c = Get-NetTCPConnection -LocalPort $PortToStop -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
	if (-not $c) { return }

	$listenerPid = [int]$c.OwningProcess
	$cmd = (Get-ProcessCommandLine -ProcessId $listenerPid)
	$cmdLower = $cmd.ToLowerInvariant()

	$looksLikeUvicorn = $cmdLower.Contains('uvicorn')
	$looksLikeManaosRpg = $cmdLower.Contains('manaos-rpg') -or $cmdLower.Contains('app:app')
	$safeToKill = $looksLikeUvicorn -and $looksLikeManaosRpg

	if (-not $safeToKill -and -not $ForceKillListener) {
		Write-Host "[manaos-rpg] Port $PortToStop is already LISTEN by pid=$listenerPid" -ForegroundColor Yellow
		if ($cmd) {
			Write-Host "[manaos-rpg] Listener cmdline: $cmd" -ForegroundColor DarkYellow
		}
		Write-Host "[manaos-rpg] Refusing to kill unknown listener. Re-run with -ForceKill or set env MANAOS_RPG_FORCE_KILL_PORT=1." -ForegroundColor Yellow
		throw "Port $PortToStop is in use."
	}

	Write-Host "[manaos-rpg] Port $PortToStop busy; stopping pid=$listenerPid" -ForegroundColor Yellow
	if ($cmd) {
		Write-Host "[manaos-rpg] Killing listener cmdline: $cmd" -ForegroundColor DarkYellow
	}
	Stop-Process -Id $listenerPid -Force -ErrorAction Stop

	$deadline = (Get-Date).AddSeconds(3)
	while ((Get-Date) -lt $deadline) {
		Start-Sleep -Milliseconds 150
		$still = Get-NetTCPConnection -LocalPort $PortToStop -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
		if (-not $still) { return }
	}
	throw "Port $PortToStop did not release after killing pid=$listenerPid."
}

$forceEnvRaw = $env:MANAOS_RPG_FORCE_KILL_PORT
if ($null -eq $forceEnvRaw) { $forceEnvRaw = '0' }
$forceByEnv = @('1','true','yes','on') -contains ([string]$forceEnvRaw).Trim().ToLowerInvariant()
$effectiveForceKill = $ForceKill.IsPresent -or $forceByEnv

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'

Stop-ListenerOnPort -PortToStop $Port -ForceKillListener:$effectiveForceKill

Set-Location $backend

Write-Host "[manaos-rpg] Installing backend deps..." -ForegroundColor Cyan
py -3.10 -m pip install -r .\requirements.txt

if ($EnableActions.IsPresent) {
	$env:MANAOS_RPG_ENABLE_ACTIONS = '1'
	Write-Host "[manaos-rpg] Actions ENABLED (MANAOS_RPG_ENABLE_ACTIONS=1)" -ForegroundColor Yellow
}

Write-Host "[manaos-rpg] Starting API on http://${BindHost}:${Port}" -ForegroundColor Green
py -3.10 -m uvicorn app:app --host $BindHost --port $Port
