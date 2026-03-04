param(
	[int]$BackendPort = 9510,
	[int]$FrontendPort = 5173,
	[switch]$SkipFirewall,
	[switch]$KeepExisting
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$stopBackendScript = Join-Path $scriptDir "stop_manaos_rpg_backend.ps1"
$stopFrontendScript = Join-Path $scriptDir "stop_manaos_rpg_frontend.ps1"
$startBackendScript = Join-Path $scriptDir "start_manaos_rpg_backend.ps1"
$startFrontendScript = Join-Path $scriptDir "start_manaos_rpg_frontend.ps1"
$statusBackendScript = Join-Path $scriptDir "status_manaos_rpg_backend.ps1"
$statusFrontendScript = Join-Path $scriptDir "status_manaos_rpg_frontend.ps1"
$firewallScript = Join-Path $scriptDir "manaos-rpg\scripts\open_firewall_ports.ps1"

foreach ($required in @($stopBackendScript, $stopFrontendScript, $startBackendScript, $startFrontendScript, $statusBackendScript, $statusFrontendScript)) {
	if (-not (Test-Path $required)) {
		throw "Required script not found: $required"
	}
}

function Get-TailscaleIPv4 {
	try {
		$ip = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*Tailscale*' -ErrorAction SilentlyContinue |
			Select-Object -ExpandProperty IPAddress -First 1
		if (-not [string]::IsNullOrWhiteSpace($ip)) {
			return [string]$ip
		}
	}
	catch {
	}
	return ""
}

function Test-IsAdmin {
	$wid = [Security.Principal.WindowsIdentity]::GetCurrent()
	$pr = New-Object Security.Principal.WindowsPrincipal($wid)
	return $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Script {
	param(
		[string]$Path,
		[string[]]$Arguments = @(),
		[int[]]$OkCodes = @(0)
	)

	$cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Path) + $Arguments
	$output = @(& pwsh @cmdArgs 2>&1 | ForEach-Object { [string]$_ })
	$exitCode = [int]$LASTEXITCODE
	if (-not ($OkCodes -contains $exitCode)) {
		$tail = ($output | Select-Object -Last 20) -join "`n"
		throw "Script failed: $Path (exit=$exitCode)`n$tail"
	}
	return $output
}

Write-Host "=== ManaOS RPG Tailscale Start ===" -ForegroundColor Cyan

if (-not $SkipFirewall.IsPresent -and (Test-Path $firewallScript)) {
	if (Test-IsAdmin) {
		Write-Host "[INFO] Opening firewall ports for RPG..." -ForegroundColor Gray
		Invoke-Script -Path $firewallScript -Arguments @('-ApiPort', "$BackendPort", '-UiPort', "$FrontendPort") | Out-Null
		Write-Host "[OK] Firewall rules ensured for TCP $BackendPort/$FrontendPort" -ForegroundColor Green
	}
	else {
		Write-Host "[WARN] Not running as Administrator, firewall rule step skipped." -ForegroundColor Yellow
		Write-Host "[WARN] If access fails, rerun this script as admin (or pass -SkipFirewall)." -ForegroundColor Yellow
	}
}

if (-not $KeepExisting.IsPresent) {
	Write-Host "[INFO] Restarting RPG services with 0.0.0.0 bind..." -ForegroundColor Gray
	Invoke-Script -Path $stopFrontendScript -Arguments @('-Port', "$FrontendPort") -OkCodes @(0)
	Invoke-Script -Path $stopBackendScript -Arguments @('-Port', "$BackendPort", '-ForceAllListeners') -OkCodes @(0)
}

Invoke-Script -Path $startBackendScript -Arguments @('-ListenHost', '0.0.0.0', '-Port', "$BackendPort") | Out-Null
Invoke-Script -Path $startFrontendScript -Arguments @('-BindAddress', '0.0.0.0', '-Port', "$FrontendPort", '-ServeMode', 'preview') | Out-Null

$backendJson = (Invoke-Script -Path $statusBackendScript -Arguments @('-BindAddress', '127.0.0.1', '-Port', "$BackendPort", '-AsJson') | Out-String | ConvertFrom-Json)
$frontendJson = (Invoke-Script -Path $statusFrontendScript -Arguments @('-BindAddress', '127.0.0.1', '-Port', "$FrontendPort", '-AsJson') | Out-String | ConvertFrom-Json)

$tailscaleIp = Get-TailscaleIPv4

Write-Host "backend_pass : $($backendJson.pass)" -ForegroundColor Gray
Write-Host "frontend_pass: $($frontendJson.pass)" -ForegroundColor Gray

if (-not [bool]$backendJson.pass -or -not [bool]$frontendJson.pass) {
	Write-Host "[ALERT] RPG startup check failed." -ForegroundColor Red
	exit 1
}

if (-not [string]::IsNullOrWhiteSpace($tailscaleIp)) {
	Write-Host "[OK] Tailscale URL (UI):  http://${tailscaleIp}:${FrontendPort}" -ForegroundColor Green
	Write-Host "[OK] Tailscale URL (API): http://${tailscaleIp}:${BackendPort}/health" -ForegroundColor Green
}
else {
	Write-Host "[WARN] Tailscale IP not found. Connect to Tailscale first, then run again." -ForegroundColor Yellow
}

Write-Host "[OK] Local URL (UI):  http://127.0.0.1:${FrontendPort}" -ForegroundColor Green
Write-Host "[OK] Local URL (API): http://127.0.0.1:${BackendPort}/health" -ForegroundColor Green

exit 0
