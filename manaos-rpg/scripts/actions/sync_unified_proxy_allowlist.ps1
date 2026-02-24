param(
  [ValidateSet('merge','overwrite')]
  [string]$Mode = 'merge',
  [ValidateSet(0,1)]
  [int]$Disable404 = 1,
  [int]$Disable404Limit = 800,
  [int]$Disable404TimeoutSec = 6
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $repoRoot 'scripts\sync_unified_proxy_from_openapi.py'

if (-not (Test-Path $script)) {
  throw "sync script not found: $script"
}

$env:MANAOS_RPG_PROXY_SYNC_MODE = $Mode

Write-Host "[manaos-rpg] Sync unified proxy allowlist (mode=$Mode)" -ForegroundColor Cyan
Write-Host "[manaos-rpg] script=$script" -ForegroundColor DarkGray

py -3.10 $script
if ($LASTEXITCODE -ne 0) {
  throw "sync failed: exit=$LASTEXITCODE"
}

if ($Disable404 -eq 1) {
  $disableScript = Join-Path $repoRoot 'scripts\disable_unified_proxy_404.py'
  if (Test-Path $disableScript) {
    $env:MANAOS_RPG_DISABLE_404_LIMIT = "$Disable404Limit"
    $env:MANAOS_RPG_DISABLE_404_TIMEOUT = "$Disable404TimeoutSec"
    Write-Host "[manaos-rpg] Auto-disable 404 rules (limit=$Disable404Limit timeout=$Disable404TimeoutSec)" -ForegroundColor DarkCyan
    py -3.10 $disableScript
  }
}

Write-Host "[manaos-rpg] OK" -ForegroundColor Green
