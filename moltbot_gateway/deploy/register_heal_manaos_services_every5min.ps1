$ErrorActionPreference = 'Stop'

# 5分おきに 18789/8088 を監視して自動復旧するタスクを登録
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\register_heal_manaos_services_every5min.ps1

$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq 'deploy') { Set-Location ..\.. }
$repoRoot = (Get-Location).Path

$scriptPath = Join-Path $repoRoot 'moltbot_gateway\deploy\heal_manaos_services.ps1'
if (-not (Test-Path $scriptPath)) {
    Write-Host 'Error: heal_manaos_services.ps1 not found.'
    exit 1
}

$taskName = 'ManaosHealServices'

# 環境によっては RepetitionInterval が使えないため、schtasks.exe で作成する（最も互換性が高い）
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $scriptPath

schtasks.exe /Create /F /SC MINUTE /MO 5 /TN $taskName /TR $cmd /RL LIMITED /RU $env:USERNAME | Out-Null

Write-Host ('OK. Registered scheduled task: {0} (every 5 minutes)' -f $taskName)
Write-Host ('Disable: Disable-ScheduledTask -TaskName "{0}"' -f $taskName)
Write-Host ('Start:   Start-ScheduledTask -TaskName "{0}"' -f $taskName)
Write-Host ('Remove: Unregister-ScheduledTask -TaskName "{0}"' -f $taskName)
