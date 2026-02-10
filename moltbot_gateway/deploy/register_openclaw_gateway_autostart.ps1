$ErrorActionPreference = 'Stop'

# Register a per-user scheduled task that starts OpenClaw Gateway at logon.
# Usage (from repo root):
#   .\moltbot_gateway\deploy\register_openclaw_gateway_autostart.ps1

$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq 'deploy') { Set-Location ..\.. }
$repoRoot = (Get-Location).Path

$runScript = Join-Path $repoRoot 'moltbot_gateway\deploy\run_openclaw_gateway_production.ps1'
if (-not (Test-Path $runScript)) {
    Write-Host 'Error: run_openclaw_gateway_production.ps1 not found.'
    exit 1
}

$taskName = 'OpenClawGateway'
$arg = ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $runScript)
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host ('OK. Registered scheduled task: {0}' -f $taskName)
Write-Host ('Disable: Disable-ScheduledTask -TaskName "{0}"' -f $taskName)
Write-Host ('Start:   Start-ScheduledTask -TaskName "{0}"' -f $taskName)
Write-Host ('Remove: Unregister-ScheduledTask -TaskName "{0}"' -f $taskName)
