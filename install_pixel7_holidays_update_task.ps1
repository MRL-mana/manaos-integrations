param(
    [string]$TaskName = "ManaOS_Pixel7_Holidays_Update_Annual",
    [string]$StartTime = "03:30",
    [string]$Month = "DEC",
    [int]$Day = 25,
    [switch]$RunAsSystem,
    [switch]$KeepBatteryRestrictions,
    [switch]$NoFallbackToCurrentUser,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobScript = Join-Path $scriptDir "update_pixel7_holidays_jp.ps1"

if (-not (Test-Path $jobScript)) {
    throw "Job script not found: $jobScript"
}

if ($Day -lt 1 -or $Day -gt 31) {
    throw "Day must be 1..31"
}

$validMonths = @('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
$monthUpper = $Month.Trim().ToUpperInvariant()
if ($monthUpper -notin $validMonths) {
    throw "Month must be JAN..DEC"
}

$taskRun = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$jobScript`" -IncludeNextYear"
$useSystemAccount = $RunAsSystem.IsPresent

function Set-TaskBatteryPolicy {
    param(
        [string]$InTaskName,
        [switch]$Skip
    )

    if ($Skip.IsPresent) {
        Write-Host "[INFO] Keep battery restrictions enabled" -ForegroundColor DarkGray
        return
    }

    try {
        $service = New-Object -ComObject 'Schedule.Service'
        $service.Connect()
        $root = $service.GetFolder('\\')
        $taskPath = if ($InTaskName.StartsWith('\\')) { $InTaskName } else { "\\$InTaskName" }
        $task = $root.GetTask($taskPath)
        if ($null -eq $task) {
            Write-Host "[WARN] Task not found for battery policy update: $InTaskName" -ForegroundColor Yellow
            return
        }

        $definition = $task.Definition
        $definition.Settings.DisallowStartIfOnBatteries = $false
        $definition.Settings.StopIfGoingOnBatteries = $false
        $definition.Settings.WakeToRun = $true
        $principal = $definition.Principal
        $userId = $principal.UserId
        if ([string]::IsNullOrWhiteSpace($userId)) {
            $userId = $null
        }
        $logonType = [int]$principal.LogonType
        $null = $root.RegisterTaskDefinition($taskPath, $definition, 6, $userId, $null, $logonType, $null)
        Write-Host "[OK] Battery policy relaxed (start/continue on battery, wake enabled)" -ForegroundColor Green
    } catch {
        $msg = $_.Exception.Message
        if ($msg -match '0x8007007B') {
            Write-Host "[INFO] Battery policy update skipped (task remains valid): $msg" -ForegroundColor DarkGray
            return
        }
        Write-Host "[WARN] Failed to update battery policy: $msg" -ForegroundColor Yellow
    }
}

Write-Host "=== Register Pixel7 Holiday Update Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MONTHLY $monthUpper/$Day $StartTime" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Script   : $jobScript" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

$createArgs = @('/Create', '/SC', 'MONTHLY', '/M', $monthUpper, '/D', "$Day", '/TN', $TaskName, '/TR', $taskRun, '/ST', $StartTime, '/F')
if ($useSystemAccount) {
    $createArgs += @('/RU', 'SYSTEM', '/RL', 'HIGHEST')
}
schtasks @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($useSystemAccount -and -not $NoFallbackToCurrentUser) {
        Write-Host "[WARN] SYSTEM registration failed. retry with current user..." -ForegroundColor Yellow
        $useSystemAccount = $false
        $createArgs = @('/Create', '/SC', 'MONTHLY', '/M', $monthUpper, '/D', "$Day", '/TN', $TaskName, '/TR', $taskRun, '/ST', $StartTime, '/F')
        schtasks @createArgs | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
        }
    } else {
        throw "Failed to create scheduled task (exit=$LASTEXITCODE)"
    }
}

Set-TaskBatteryPolicy -InTaskName $TaskName -Skip:$KeepBatteryRestrictions

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
Write-Host "[OK] Effective Account : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}
