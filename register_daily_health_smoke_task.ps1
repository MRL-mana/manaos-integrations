param(
    [string]$TaskName = "ManaOS_Daily_Health_Smoke",
    [string]$DailyTime = "09:10",
    [string]$Distro = "Ubuntu-22.04",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
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

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if (-not $PSBoundParameters.ContainsKey('WebhookFormat') -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
    $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
    if ($envFormat -in @('generic', 'slack', 'discord')) {
        $WebhookFormat = $envFormat
    }
}
if (-not $NotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
    $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
    if ($notifyRaw -in @('1', 'true', 'yes', 'on', 'enabled')) {
        $NotifyOnSuccess = $true
    }
}

$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path $psExe)) {
    $psExe = "powershell.exe"
}

$taskArgs = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $targetScript + '" -Distro "' + $Distro + '" -RecoveryTimeoutSec ' + $RecoveryTimeoutSec
if ($Recover) { $taskArgs += ' -Recover' }
if ($StrictApi) { $taskArgs += ' -StrictApi' }
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $escapedWebhookUrl = $WebhookUrl.Replace('"', '""')
    $taskArgs += ' -WebhookUrl "' + $escapedWebhookUrl + '"'
}
$taskArgs += ' -WebhookFormat ' + $WebhookFormat
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
    $escapedWebhookMention = $WebhookMention.Replace("'", "''")
    $taskArgs += " -WebhookMention '" + $escapedWebhookMention + "'"
}
if ($NotifyOnSuccess) { $taskArgs += ' -NotifyOnSuccess' }

$mode = "scheduled_task"

try {
    $trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
    $action = New-ScheduledTaskAction -Execute $psExe -Argument $taskArgs
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
    if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        $escapedWebhookUrlRun = $WebhookUrl.Replace('"', '""')
        $runCmd += ' -WebhookUrl "' + $escapedWebhookUrlRun + '"'
    }
    $runCmd += ' -WebhookFormat ' + $WebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
        $escapedWebhookMentionRun = $WebhookMention.Replace("'", "''")
        $runCmd += " -WebhookMention '" + $escapedWebhookMentionRun + "'"
    }
    if ($NotifyOnSuccess) { $runCmd += ' -NotifyOnSuccess' }
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
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    webhook_mention = $WebhookMention
    notify_on_success = [bool]$NotifyOnSuccess
    script = $targetScript
}

$statusPath = Join-Path $logsDir "daily_health_smoke_task_status.json"
$status | ConvertTo-Json -Depth 6 | Set-Content -Path $statusPath -Encoding UTF8
Write-Ok "Status written: $statusPath"
