param(
    [string]$TaskName = "ManaOS_OpenWebUI_DailyHealth",
    [string]$DailyTime = "09:00",
    [int]$MaxAgeMinutes = 180,
    [switch]$RequireStartupSource,
    [switch]$AutoRecoverOnFailure,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [int]$VerifyDelaySeconds = 180
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Resolve-NotifySettings {
    param(
        [string]$InWebhookUrl,
        [string]$InWebhookFormat,
        [string]$InWebhookMention,
        [bool]$InNotifyOnSuccess
    )

    $resolvedUrl = $InWebhookUrl
    if ([string]::IsNullOrWhiteSpace($resolvedUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
        $resolvedUrl = $env:MANAOS_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
        $resolvedUrl = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")
    }

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $envFormat
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User"))) {
        $userFormat = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User").Trim().ToLowerInvariant()
        if ($userFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $userFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }
    if ([string]::IsNullOrWhiteSpace($resolvedMention)) {
        $resolvedMention = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", "User")
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRaw -in @("1", "true", "yes", "on"))
    }
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User"))) {
        $notifyRawUser = [Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User").Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRawUser -in @("1", "true", "yes", "on"))
    }

    return [ordered]@{
        webhook_url = $resolvedUrl
        webhook_format = $resolvedFormat
        webhook_mention = $resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
    }
}

function Ensure-DailyTask {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$CheckScript,
        [Parameter(Mandatory = $true)]
        [int]$AgeMinutes,
        [bool]$RequireSource = $false,
        [bool]$AutoRecover = $false,
        [string]$HookFormat = "discord",
        [string]$HookUrl = "",
        [string]$HookMention = "",
        [bool]$NotifySuccess = $false,
        [int]$DelaySec = 180
    )

    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) { $psExe = "powershell.exe" }

    $args = '-NoProfile -ExecutionPolicy Bypass -File "' + $CheckScript + '" -MaxAgeMinutes ' + $AgeMinutes
    if ($RequireSource) {
        $args += ' -RequireStartupSource'
    }
    if ($AutoRecover) {
        $args += ' -AutoRecoverOnFailure'
    }
    $args += ' -WebhookFormat ' + $HookFormat
    if (-not [string]::IsNullOrWhiteSpace($HookUrl)) {
        $args += ' -WebhookUrl "' + $HookUrl + '"'
    }
    if (-not [string]::IsNullOrWhiteSpace($HookMention)) {
        $args += ' -WebhookMention "' + $HookMention + '"'
    }
    if ($NotifySuccess) {
        $args += ' -NotifyOnSuccess'
    }
    $args += ' -VerifyDelaySeconds ' + $DelaySec

    $trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
    $action = New-ScheduledTaskAction -Execute $psExe -Argument $args
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Daily health check for OpenWebUI production" -Force | Out-Null
}

function Ensure-RunEntryFallback {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EntryName,
        [Parameter(Mandatory = $true)]
        [string]$CheckScript,
        [Parameter(Mandatory = $true)]
        [int]$AgeMinutes,
        [bool]$RequireSource = $false,
        [bool]$AutoRecover = $false,
        [string]$HookFormat = "discord",
        [string]$HookUrl = "",
        [string]$HookMention = "",
        [bool]$NotifySuccess = $false,
        [int]$DelaySec = 180
    )

    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) { $psExe = "powershell.exe" }

    $cmd = '"' + $psExe + '" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& ''' + $CheckScript + ''' -MaxAgeMinutes ' + $AgeMinutes
    if ($RequireSource) {
        $cmd += ' -RequireStartupSource'
    }
    if ($AutoRecover) {
        $cmd += ' -AutoRecoverOnFailure'
    }
    $cmd += ' -WebhookFormat ' + $HookFormat
    if (-not [string]::IsNullOrWhiteSpace($HookUrl)) {
        $cmd += ' -WebhookUrl ''' + $HookUrl + ''''
    }
    if (-not [string]::IsNullOrWhiteSpace($HookMention)) {
        $cmd += ' -WebhookMention ''' + $HookMention + ''''
    }
    if ($NotifySuccess) {
        $cmd += ' -NotifyOnSuccess'
    }
    $cmd += ' -VerifyDelaySeconds ' + $DelaySec
    $cmd += '"'

    if (-not (Test-Path $runKey)) {
        New-Item -Path $runKey -Force | Out-Null
    }
    Set-ItemProperty -Path $runKey -Name $EntryName -Value $cmd -Type String
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptRoot "logs"
$checkScript = Join-Path $scriptRoot "check_openwebui_production.ps1"

if (-not (Test-Path $checkScript)) {
    throw "Missing script: $checkScript"
}

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

Write-Host "Register OpenWebUI daily health" -ForegroundColor Cyan

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

$mode = "none"
try {
    Ensure-DailyTask -Name $TaskName -CheckScript $checkScript -AgeMinutes $MaxAgeMinutes -RequireSource ([bool]$RequireStartupSource) -AutoRecover ([bool]$AutoRecoverOnFailure) -HookFormat $WebhookFormat -HookUrl $WebhookUrl -HookMention $WebhookMention -NotifySuccess ([bool]$NotifyOnSuccess) -DelaySec $VerifyDelaySeconds
    $mode = "scheduled_task"
    Write-Ok "Scheduled daily task ensured: $TaskName ($DailyTime)"
}
catch {
    Write-Warn "Daily scheduled task registration failed: $($_.Exception.Message)"
    Ensure-RunEntryFallback -EntryName $TaskName -CheckScript $checkScript -AgeMinutes $MaxAgeMinutes -RequireSource ([bool]$RequireStartupSource) -AutoRecover ([bool]$AutoRecoverOnFailure) -HookFormat $WebhookFormat -HookUrl $WebhookUrl -HookMention $WebhookMention -NotifySuccess ([bool]$NotifyOnSuccess) -DelaySec $VerifyDelaySeconds
    $mode = "run_key"
    Write-Ok "Run entry fallback ensured: $TaskName"
}

$state = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    mode = $mode
    task_name = $TaskName
    daily_time = $DailyTime
    max_age_minutes = $MaxAgeMinutes
    require_startup_source = [bool]$RequireStartupSource
    auto_recover_on_failure = [bool]$AutoRecoverOnFailure
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    notify_on_success = [bool]$NotifyOnSuccess
    verify_delay_seconds = $VerifyDelaySeconds
    check_script = $checkScript
}

$statePath = Join-Path $logsDir "daily_health_registration_status.json"
$state | ConvertTo-Json -Depth 6 | Set-Content -Path $statePath -Encoding UTF8
Write-Ok "Registration status written: $statePath"
