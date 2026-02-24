param()

$ErrorActionPreference = 'Stop'

$taskName = 'ManaOS-RPG-AlwaysOn'
schtasks /Query /TN $taskName *> $null 2>&1
if ($LASTEXITCODE -ne 0) {
	Write-Host "[manaos-rpg] Autostart task not found: $taskName" -ForegroundColor Yellow
	exit 0
}

schtasks /Delete /TN $taskName /F | Out-Null
Write-Host "[manaos-rpg] Removed autostart task: $taskName" -ForegroundColor Green
