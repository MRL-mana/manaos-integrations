param(
    [string]$TaskName = 'ManaOS_v114_Waiting_Alert_10min',
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    $missing = [ordered]@{
        exists = $false
        task_name = $TaskName
        error = 'task_not_found'
        source = 'Get-ScheduledTask'
    }

    if ($AsJson) {
        $missing | ConvertTo-Json -Depth 6
    }
    else {
        Write-Host '=== v114 Waiting Alert Task Status ===' -ForegroundColor Cyan
        Write-Host "TaskName: $TaskName" -ForegroundColor Gray
        Write-Host '[INFO] Task not found' -ForegroundColor Yellow
    }
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
$action = $task.Actions | Select-Object -First 1
$triggerNames = @()
if ($task.Triggers) {
    $triggerNames = @($task.Triggers | ForEach-Object { [string]$_.CimClass.CimClassName })
}

$nextRunTime = ''
if ($info -and $info.NextRunTime) {
    $nextRunTime = ([datetime]$info.NextRunTime).ToString('o')
}

$lastRunTime = ''
if ($info -and $info.LastRunTime) {
    $lastRunTime = ([datetime]$info.LastRunTime).ToString('o')
}

$lastTaskResult = ''
if ($info) {
    $lastTaskResult = [string]$info.LastTaskResult
}

$runAsUser = ''
if ($task.Principal) {
    $runAsUser = [string]$task.Principal.UserId
}

$command = ''
if ($action) {
    $command = (([string]$action.Execute + ' ' + [string]$action.Arguments).Trim())
}

$result = [ordered]@{
    exists = $true
    task_name = $TaskName
    state = [string]$task.State
    next_run_time = $nextRunTime
    last_run_time = $lastRunTime
    last_task_result = $lastTaskResult
    run_as_user = $runAsUser
    command = $command
    schedule_type = ($triggerNames -join ',')
    source = 'Get-ScheduledTask'
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host '=== v114 Waiting Alert Task Status ===' -ForegroundColor Cyan
Write-Host "TaskName        : $($result.task_name)" -ForegroundColor Gray
Write-Host "State           : $($result.state)" -ForegroundColor Gray
Write-Host "Next Run        : $($result.next_run_time)" -ForegroundColor Gray
Write-Host "Last Run        : $($result.last_run_time)" -ForegroundColor Gray
Write-Host "Last Result     : $($result.last_task_result)" -ForegroundColor Gray
Write-Host "Run As User     : $($result.run_as_user)" -ForegroundColor Gray
Write-Host "Schedule Type   : $($result.schedule_type)" -ForegroundColor Gray
Write-Host "Command         : $($result.command)" -ForegroundColor DarkGray

exit 0
