param()

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$composeDir = Split-Path -Parent $root  # manaos-rpg/..
$composeDir = Join-Path $composeDir '..'
$composeDir = (Resolve-Path $composeDir).Path

$env:MRL_FWPKM_WRITE_ENABLED = '0'
$env:MRL_FWPKM_WRITE_MODE = 'readonly'
$env:MRL_FWPKM_WRITE_SAMPLE_RATE = '0.1'
$env:MRL_FWPKM_REVIEW_EFFECT = '0'

Write-Host "[mrl-memory] Disabling write: mode=$($env:MRL_FWPKM_WRITE_MODE) write_enabled=$($env:MRL_FWPKM_WRITE_ENABLED)" -ForegroundColor Yellow

Push-Location $composeDir
try {
	docker compose up -d --force-recreate mrl-memory
	Start-Sleep -Seconds 2
	try {
		Invoke-RestMethod http://127.0.0.1:9507/api/metrics -TimeoutSec 15 |
			Select-Object -ExpandProperty config |
			ConvertTo-Json -Depth 4 |
			Write-Host
	} catch {
		Write-Host "[mrl-memory] metrics check failed: $($_.Exception.Message)" -ForegroundColor Red
	}
} finally {
	Pop-Location
}
