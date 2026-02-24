param(
  [int]$Limit = 800,
  [int]$TimeoutSec = 6
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $repoRoot 'scripts\disable_unified_proxy_404.py'

if (-not (Test-Path $script)) {
  throw "script not found: $script"
}

$env:MANAOS_RPG_DISABLE_404_LIMIT = "$Limit"
$env:MANAOS_RPG_DISABLE_404_TIMEOUT = "$TimeoutSec"

Write-Host "[manaos-rpg] Disable 404 rules in unified_proxy.yaml" -ForegroundColor Cyan
py -3.10 $script
if ($LASTEXITCODE -ne 0) {
  throw "disable_404 failed: exit=$LASTEXITCODE"
}
