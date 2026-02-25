param(
	[switch]$Lan,
	[switch]$EnableActions,
	[switch]$EnableUnifiedWrite,
	[int]$ApiPort = 9510,
	[int]$UiPort = 5173
)

$ErrorActionPreference = 'Stop'

$taskName = 'ManaOS-RPG-AlwaysOn'
$runner = Join-Path $PSScriptRoot 'run_always_on.ps1'

$psArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', "`"$runner`"", '-ApiPort', $ApiPort, '-UiPort', $UiPort)
if ($Lan.IsPresent) { $psArgs += '-Lan' }
if ($EnableActions.IsPresent) { $psArgs += '-EnableActions' }
if ($EnableUnifiedWrite.IsPresent) { $psArgs += '-EnableUnifiedWrite' }

$cmd = 'pwsh ' + ($psArgs -join ' ')

# 既存があれば更新
schtasks /Query /TN $taskName *> $null 2>&1
if ($LASTEXITCODE -eq 0) {
	schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /SC ONLOGON /RL LIMITED /TR $cmd /F | Out-Null
Write-Host "[manaos-rpg] Installed autostart task: $taskName" -ForegroundColor Green
Write-Host "[manaos-rpg] It will start at next logon. Run now:" -ForegroundColor Cyan
Write-Host "  pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_always_on.ps1" -ForegroundColor Cyan
