param(
	[int]$ApiPort = 9510,
	[int]$UiPort = 5173
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
	$wid = [Security.Principal.WindowsIdentity]::GetCurrent()
	$pr = New-Object Security.Principal.WindowsPrincipal($wid)
	if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
		throw '管理者権限が必要です。管理者でPowerShellを開いて実行してください。'
	}
}

Assert-Admin

$rules = @(
	@{ Name="ManaOS-RPG-API-$ApiPort"; Port=$ApiPort },
	@{ Name="ManaOS-RPG-UI-$UiPort"; Port=$UiPort }
)

foreach ($r in $rules) {
	$name = $r.Name
	$port = [int]$r.Port
	if (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue) {
		Write-Host "[manaos-rpg] Firewall rule exists: $name" -ForegroundColor DarkGreen
		continue
	}
	New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
	Write-Host "[manaos-rpg] Firewall rule added: $name (TCP $port)" -ForegroundColor Green
}
