param(
    [string]$TaskName = "ManaOS_Daily_Health_Smoke",
    [string]$DailyTime = "09:10",
    [string]$Distro = "Ubuntu-22.04",
    [switch]$Recover,
    [switch]$StrictApi,
    [int]$RecoveryTimeoutSec = 120,
    [switch]$RegisterRunKeyFallback
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetScript = Join-Path $scriptRoot "daily_health_smoke.ps1"
$logsDir = Join-Path $scriptRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

if (-not (Test-Path $targetScript)) {
    throw "Missing script: $targetScript"
}

$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path $psExe)) {
    $psExe = "powershell.exe"
}

$args = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $targetScript + '" -Distro "' + $Distro + '" -RecoveryTimeoutSec ' + $RecoveryTimeoutSec
if ($Recover) { $args += ' -Recover' }
if ($StrictApi) { $args += ' -StrictApi' }

$mode = "scheduled_task"

try {
    $trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
    $action = New-ScheduledTaskAction -Execute $psExe -Argument $args
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Daily health smoke for ManaOS" -Force | Out-Null
    Write-Ok "Scheduled task ensured: $TaskName ($DailyTime)"
}
catch {
    if (-not $RegisterRunKeyFallback) {
        throw
    }

    Write-Warn "Scheduled task registration failed, fallback to HKCU Run: $($_.Exception.Message)"
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if (-not (Test-Path $runKey)) {
        New-Item -Path $runKey -Force | Out-Null
    }

    $runCmd = '"' + $psExe + '" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $targetScript + '" -Distro "' + $Distro + '" -RecoveryTimeoutSec ' + $RecoveryTimeoutSec
    if ($Recover) { $runCmd += ' -Recover' }
    if ($StrictApi) { $runCmd += ' -StrictApi' }
    Set-ItemProperty -Path $runKey -Name $TaskName -Value $runCmd -Type String

    $mode = "run_key"
    Write-Ok "Run key fallback ensured: $TaskName"
}

$status = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    mode = $mode
    task_name = $TaskName
    daily_time = $DailyTime
    distro = $Distro
    recover = [bool]$Recover
    strict_api = [bool]$StrictApi
    recovery_timeout_sec = $RecoveryTimeoutSec
    script = $targetScript
}

$statusPath = Join-Path $logsDir "daily_health_smoke_task_status.json"
$status | ConvertTo-Json -Depth 6 | Set-Content -Path $statusPath -Encoding UTF8
Write-Ok "Status written: $statusPath"
