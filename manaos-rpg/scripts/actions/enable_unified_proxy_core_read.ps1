param(
  [ValidateSet(0,1)]
  [int]$DryRun = 0
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $repoRoot 'scripts\enable_unified_proxy_core_read.py'

if (-not (Test-Path $script)) {
  throw "enable script not found: $script"
}

if ($DryRun -eq 1) {
  $env:MANAOS_RPG_ENABLE_CORE_READ_DRYRUN = '1'
} else {
  $env:MANAOS_RPG_ENABLE_CORE_READ_DRYRUN = '0'
}

Write-Host "[manaos-rpg] Enable core read-only allowlist rules (dry_run=$DryRun)" -ForegroundColor Cyan
py -3.10 $script
if ($LASTEXITCODE -ne 0) {
  throw "enable_core_read failed: exit=$LASTEXITCODE"
}

Write-Host "[manaos-rpg] OK" -ForegroundColor Green
