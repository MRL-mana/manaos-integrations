param(
	[string]$BindHost = '127.0.0.1',
	[int]$Port = 9510,
	[switch]$ForceKill,
	[switch]$EnableActions,
	[switch]$EnableUnifiedWrite,
	[switch]$EnableUnifiedDangerous,
	[switch]$Lan
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
	$deadline = (Get-Date).AddSeconds(6)
	while ((Get-Date) -lt $deadline) {
		$listeners = @(Get-NetTCPConnection -LocalPort $PortToStop -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
		if ($listeners.Count -eq 0) { return $true }

		foreach ($listenerPid in $listeners) {
			$pidInt = [int]$listenerPid
			$cmd = (Get-ProcessCommandLine -ProcessId $pidInt)
			$cmdLower = $cmd.ToLowerInvariant()
			$procName = ''
			$procPath = ''
			try {
				$p = Get-Process -Id $pidInt -ErrorAction Stop
				$procName = [string]$p.ProcessName
				$procPath = [string]$p.Path
			} catch {}

			$looksLikeUvicorn = $cmdLower.Contains('uvicorn')
			$looksLikeManaosRpg = $cmdLower.Contains('manaos-rpg') -or $cmdLower.Contains('app:app')
			$looksLikeBackendPython = ($procName -ieq 'python') -and ($procPath.ToLowerInvariant().Contains('.venv\scripts\python.exe'))
			$safeToKill = ($looksLikeUvicorn -and $looksLikeManaosRpg) -or ($looksLikeBackendPython -and [string]::IsNullOrWhiteSpace($cmd))

			if (-not $safeToKill -and -not $ForceKillListener) {
				Write-Host "[manaos-rpg] Port $PortToStop is already LISTEN by pid=$pidInt" -ForegroundColor Yellow
				if ($cmd) {
					Write-Host "[manaos-rpg] Listener cmdline: $cmd" -ForegroundColor DarkYellow
				}
				Write-Host "[manaos-rpg] Keeping existing listener as-is. Re-run with -ForceKill (or env MANAOS_RPG_FORCE_KILL_PORT=1) to replace it." -ForegroundColor Yellow
				return $false
			}

			Write-Host "[manaos-rpg] Port $PortToStop busy; stopping pid=$pidInt" -ForegroundColor Yellow
			if ($cmd) {
				Write-Host "[manaos-rpg] Killing listener cmdline: $cmd" -ForegroundColor DarkYellow
			}
			Stop-Process -Id $pidInt -Force -ErrorAction SilentlyContinue
		}

		Start-Sleep -Milliseconds 250
	}

	$remaining = @(Get-NetTCPConnection -LocalPort $PortToStop -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
	if ($remaining.Count -eq 0) { return $true }
	throw "Port $PortToStop did not release after killing listeners."
}

$forceEnvRaw = $env:MANAOS_RPG_FORCE_KILL_PORT
if ($null -eq $forceEnvRaw) { $forceEnvRaw = '0' }
$forceByEnv = @('1','true','yes','on') -contains ([string]$forceEnvRaw).Trim().ToLowerInvariant()
$effectiveForceKill = $ForceKill.IsPresent -or $forceByEnv

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'

$portReleased = Stop-ListenerOnPort -PortToStop $Port -ForceKillListener:$effectiveForceKill
if (-not $portReleased) {
	Write-Host "[manaos-rpg] Existing backend listener detected on port $Port; skip starting a new instance." -ForegroundColor Green
	exit 0
}

Set-Location $backend

Write-Host "[manaos-rpg] Installing backend deps..." -ForegroundColor Cyan
py -3.10 -m pip install -r .\requirements.txt

if ($Lan.IsPresent) {
	$BindHost = '0.0.0.0'
	# CORS: Vite(5173) からAPI(9510)にアクセスするための最小セット
	# LANアクセス時はIP/ホスト名が変わるので、検出できる範囲を足す（必要なら上書き可能）
	if (-not $env:MANAOS_CORS_ORIGINS) {
		$origins = New-Object System.Collections.Generic.List[string]
		$origins.Add('http://localhost:5173')
		$origins.Add('http://127.0.0.1:5173')
		$origins.Add("http://$env:COMPUTERNAME:5173")
		try {
			$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
				Where-Object { $_.IPAddress -and $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } |
				Select-Object -ExpandProperty IPAddress
			foreach ($ip in ($ips | Select-Object -Unique)) {
				$origins.Add("http://$ip:5173")
			}
		} catch {}
		$env:MANAOS_CORS_ORIGINS = ($origins | Select-Object -Unique) -join ','
		Write-Host "[manaos-rpg] MANAOS_CORS_ORIGINS auto-set for LAN" -ForegroundColor Yellow
	}
}

if ($EnableActions.IsPresent) {
	$env:MANAOS_RPG_ENABLE_ACTIONS = '1'
	Write-Host "[manaos-rpg] Actions ENABLED (MANAOS_RPG_ENABLE_ACTIONS=1)" -ForegroundColor Yellow
}

if ($EnableUnifiedWrite.IsPresent) {
	$env:MANAOS_RPG_ENABLE_UNIFIED_WRITE = '1'
	Write-Host "[manaos-rpg] Unified WRITE ENABLED (MANAOS_RPG_ENABLE_UNIFIED_WRITE=1)" -ForegroundColor Yellow
}

if ($EnableUnifiedDangerous.IsPresent) {
	$env:MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS = '1'
	Write-Host "[manaos-rpg] Unified DANGEROUS ENABLED (MANAOS_RPG_ENABLE_UNIFIED_DANGEROUS=1)" -ForegroundColor Yellow
}

Write-Host "[manaos-rpg] Starting API on http://${BindHost}:${Port}" -ForegroundColor Green
py -3.10 -m uvicorn app:app --host $BindHost --port $Port
