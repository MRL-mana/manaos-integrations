param(
  [int]$Limit = 400,
  [double]$TimeoutSec = 2.0,
  [int]$MaxEnable = 60
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $repoRoot 'scripts\enable_unified_proxy_read_exists.py'

if (-not (Test-Path $script)) {
  throw "enable script not found: $script"
}

$env:MANAOS_RPG_ENABLE_READ_EXISTS_LIMIT = "$Limit"
$env:MANAOS_RPG_ENABLE_READ_EXISTS_TIMEOUT = "$TimeoutSec"
$env:MANAOS_RPG_ENABLE_READ_EXISTS_MAX = "$MaxEnable"

Write-Host "[manaos-rpg] Enable read-only rules that exist (limit=$Limit timeout=$TimeoutSec max=$MaxEnable)" -ForegroundColor Cyan
py -3.10 $script
if ($LASTEXITCODE -ne 0) {
  throw "enable_read_exists failed: exit=$LASTEXITCODE"
}

Write-Host "[manaos-rpg] OK" -ForegroundColor Green
