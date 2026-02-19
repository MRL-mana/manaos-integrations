param(
    [string]$TaskName = "ManaOS_OpenWebUI_Verify_OnLogon",
    [int]$DelaySeconds = 180,
    [switch]$RunNow,
    [string]$WebhookUrl = "",
    [switch]$NotifyOnSuccess,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "generic",
    [string]$WebhookMention = ""
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

function Ensure-VerifyScheduledTask {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [int]$DelaySec = 180,
        [string]$HookUrl = "",
        [bool]$NotifySuccess = $false,
        [string]$HookFormat = "generic",
        [string]$HookMention = ""
    )

    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) { $psExe = "powershell.exe" }

    $escapedScript = $ScriptPath.Replace("'", "''")
    $escapedLog = $LogPath.Replace("'", "''")
    $notifyArgs = ""
    if (-not [string]::IsNullOrWhiteSpace($HookUrl)) {
        $escapedHook = $HookUrl.Replace("'", "''")
        $notifyArgs += " -WebhookUrl '" + $escapedHook + "'"
    }
    $notifyArgs += " -WebhookFormat " + $HookFormat
    if (-not [string]::IsNullOrWhiteSpace($HookMention)) {
        $escapedMention = $HookMention.Replace("'", "''")
        $notifyArgs += " -WebhookMention '" + $escapedMention + "'"
    }
    if ($NotifySuccess) {
        $notifyArgs += " -NotifyOnSuccess"
    }

    $args = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds ' + $DelaySec + '; & ''' + $escapedScript + ''' -RequireStartupSource' + $notifyArgs + ' *> ''' + $escapedLog + '''"'

    $action = New-ScheduledTaskAction -Execute $psExe -Argument $args
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Verify OpenWebUI autostart after logon" -Force | Out-Null
}

function Ensure-VerifyRunEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EntryName,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [int]$DelaySec = 180,
        [string]$HookUrl = "",
        [bool]$NotifySuccess = $false,
        [string]$HookFormat = "generic",
        [string]$HookMention = ""
    )

    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    if (-not (Test-Path $psExe)) { $psExe = "powershell.exe" }

    $notifyArgs = ""
    if (-not [string]::IsNullOrWhiteSpace($HookUrl)) {
        $notifyArgs += ' -WebhookUrl ''' + $HookUrl + ''''
    }
    $notifyArgs += ' -WebhookFormat ' + $HookFormat
    if (-not [string]::IsNullOrWhiteSpace($HookMention)) {
        $notifyArgs += ' -WebhookMention ''' + $HookMention + ''''
    }
    if ($NotifySuccess) {
        $notifyArgs += ' -NotifyOnSuccess'
    }

    $cmd = '"' + $psExe + '" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds ' + $DelaySec + '; & ''' + $ScriptPath + ''' -RequireStartupSource' + $notifyArgs + ' *> ''' + $LogPath + '''"'
    if (-not (Test-Path $runKey)) {
        New-Item -Path $runKey -Force | Out-Null
    }
    Set-ItemProperty -Path $runKey -Name $EntryName -Value $cmd -Type String
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$verifyScript = Join-Path $scriptRoot "verify_openwebui_autostart.ps1"
$logsDir = Join-Path $scriptRoot "logs"
$verifyLog = Join-Path $logsDir "verify_openwebui_autostart_last.log"
$mode = "none"

if (-not (Test-Path $verifyScript)) {
    throw "Verifier script not found: $verifyScript"
}

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

Write-Host "Register OpenWebUI verify autorun" -ForegroundColor Cyan

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

try {
    Ensure-VerifyScheduledTask -Name $TaskName -ScriptPath $verifyScript -LogPath $verifyLog -DelaySec $DelaySeconds -HookUrl $WebhookUrl -NotifySuccess ([bool]$NotifyOnSuccess) -HookFormat $WebhookFormat -HookMention $WebhookMention
    $mode = "scheduled_task"
    Write-Ok "Scheduled task ensured: $TaskName"
}
catch {
    Write-Warn "Scheduled task registration failed: $($_.Exception.Message)"
    Ensure-VerifyRunEntry -EntryName $TaskName -ScriptPath $verifyScript -LogPath $verifyLog -DelaySec $DelaySeconds -HookUrl $WebhookUrl -NotifySuccess ([bool]$NotifyOnSuccess) -HookFormat $WebhookFormat -HookMention $WebhookMention
    $mode = "run_key"
    Write-Ok "Run entry ensured: $TaskName"
}

if ($RunNow) {
    try {
        $runParams = @{
            RequireStartupSource = $true
        }
        if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
            $runParams.WebhookUrl = $WebhookUrl
        }
        $runParams.WebhookFormat = $WebhookFormat
        if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) {
            $runParams.WebhookMention = $WebhookMention
        }
        if ($NotifyOnSuccess) {
            $runParams.NotifyOnSuccess = $true
        }
        & $verifyScript @runParams *> $verifyLog
        Write-Ok "Verifier executed immediately"
    }
    catch {
        Write-Warn "Immediate verifier execution failed: $($_.Exception.Message)"
    }
}

$state = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    mode = $mode
    task_name = $TaskName
    delay_seconds = $DelaySeconds
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    notify_on_success = [bool]$NotifyOnSuccess
    webhook_format = $WebhookFormat
    webhook_mention = $WebhookMention
    verify_script = $verifyScript
    verify_log = $verifyLog
}

$statePath = Join-Path $logsDir "verify_autorun_registration_status.json"
$state | ConvertTo-Json -Depth 6 | Set-Content -Path $statePath -Encoding UTF8
Write-Ok "Registration status written: $statePath"
