param(
    [string]$RepoRoot = "",
    [switch]$SkipRegisteredTaskAudit,
    [switch]$AsJson,
    [switch]$RequirePass
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = $scriptDir
}

if (-not (Test-Path $RepoRoot)) {
    throw "RepoRoot not found: $RepoRoot"
}

$hiddenPattern = '(?im)(-windowstyle\s+hidden|-w\s+hidden|\s/B\b)'
$shellPattern = '(?im)(pwsh|powershell(?:\.exe)?)'

$scriptOffenders = New-Object System.Collections.Generic.List[object]
$scriptPatterns = @(
    'install_*task*.ps1',
    'register_*task*.ps1',
    'register_schedule_tasks.ps1',
    'register_moltbot_schedule_tasks.ps1',
    'register_openwebui_daily_health.ps1',
    'schedule_*.ps1',
    'setup_*autostart*.ps1',
    'setup_autostart*.ps1',
    'setup_all_systems.ps1',
    'setup_always_running_services.ps1',
    'setup_mrl_memory_autostart*.ps1',
    'setup_tool_server_auto_start.ps1',
    'start_openwebui_tailscale.ps1'
)

$scriptMap = @{}
foreach ($pattern in $scriptPatterns) {
    foreach ($item in @(Get-ChildItem -Path $RepoRoot -Filter $pattern -File -ErrorAction SilentlyContinue)) {
        $scriptMap[$item.FullName] = $item
    }
}
$installerScripts = @($scriptMap.Values | Sort-Object FullName)
$managedTaskNames = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
foreach ($script in $installerScripts) {
    $raw = Get-Content -Path $script.FullName -Raw

    $taskNameMatches = [regex]::Matches($raw, '(?im)^\s*\[string\]\s*\$TaskName\s*=\s*"([^"]+)"')
    foreach ($match in $taskNameMatches) {
        $null = $managedTaskNames.Add($match.Groups[1].Value)
    }
    $taskNameMatches = [regex]::Matches($raw, '(?im)\b-TaskName\s+"([^"]+)"')
    foreach ($match in $taskNameMatches) {
        $null = $managedTaskNames.Add($match.Groups[1].Value)
    }
    $taskNameMatches = [regex]::Matches($raw, '(?im)\b/TN\s+"([^"]+)"')
    foreach ($match in $taskNameMatches) {
        $null = $managedTaskNames.Add($match.Groups[1].Value)
    }

    $hasPowerShellTaskAction = ($raw -match '(?is)New-ScheduledTaskAction[^\r\n]*-Execute\s+"?powershell(?:\.exe)?"?')
    $hasPowerShellTaskRun = ($raw -match '(?im)\bschtasks\b[^\r\n]*/Create[^\r\n]*/TR\s+[^\r\n]*(pwsh|powershell(?:\.exe)?)')
    $hasHidden = ($raw -match $hiddenPattern)
    if (($hasPowerShellTaskAction -or $hasPowerShellTaskRun) -and -not $hasHidden) {
        $scriptOffenders.Add([pscustomobject]@{
            path = $script.FullName
            reason = 'scheduled task command appears to lack hidden window switch'
        })
    }
}

$registeredOffenders = New-Object System.Collections.Generic.List[object]
if (-not $SkipRegisteredTaskAudit) {
    # schtasks の代わりに Get-ScheduledTask API を使用（日本語環境でのエンコーディング問題を回避）
    $allTasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.State -ne 'Disabled' }
    foreach ($task in $allTasks) {
        try {
            $a = $task.Actions[0]
            $exe = [string]$a.Execute
            $args = [string]$a.Arguments
            $taskToRun = "$exe $args".Trim()
            if ($exe -match $shellPattern -and -not ($taskToRun -match $hiddenPattern)) {
                $registeredOffenders.Add([pscustomobject]@{
                    task_name  = $task.TaskName
                    task_to_run = $taskToRun
                    reason = 'registered task command uses PowerShell without hidden window switch'
                })
            }
        } catch {}
    }
}

$installerOffendersArray = @($scriptOffenders.ToArray())
$registeredOffendersArray = @($registeredOffenders.ToArray())

$payload = @{
    repo_root = $RepoRoot
    installer_script_count = $installerScripts.Count
    managed_task_name_count = $managedTaskNames.Count
    installer_offender_count = $scriptOffenders.Count
    installer_offenders = $installerOffendersArray
    registered_task_audit_enabled = (-not $SkipRegisteredTaskAudit)
    registered_offender_count = $registeredOffenders.Count
    registered_offenders = $registeredOffendersArray
    ok = ($scriptOffenders.Count -eq 0 -and $registeredOffenders.Count -eq 0)
}

Write-Host "=== Scheduled Tasks Hidden Guard Doctor ===" -ForegroundColor Cyan
Write-Host "repo_root: $RepoRoot" -ForegroundColor Gray
Write-Host "installer_script_count: $($payload.installer_script_count)" -ForegroundColor Gray
Write-Host "managed_task_name_count: $($payload.managed_task_name_count)" -ForegroundColor Gray
Write-Host "installer_offender_count: $($payload.installer_offender_count)" -ForegroundColor Gray
Write-Host "registered_task_audit_enabled: $($payload.registered_task_audit_enabled)" -ForegroundColor Gray
Write-Host "registered_offender_count: $($payload.registered_offender_count)" -ForegroundColor Gray

if ($payload.installer_offender_count -gt 0) {
    Write-Host "--- installer_offenders ---" -ForegroundColor Yellow
    $payload.installer_offenders | ForEach-Object { Write-Host $_.path -ForegroundColor Yellow }
}
if ($payload.registered_offender_count -gt 0) {
    Write-Host "--- registered_offenders ---" -ForegroundColor Yellow
    $payload.registered_offenders | ForEach-Object {
        Write-Host ("{0} => {1}" -f $_.task_name, $_.task_to_run) -ForegroundColor Yellow
    }
}

if ($AsJson) {
    Write-Output ($payload | ConvertTo-Json -Depth 8)
}

if ($payload.ok) {
    exit 0
}

exit 1
