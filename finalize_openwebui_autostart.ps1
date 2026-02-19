param(
    [string]$StartupTaskName = "ManaOS_OpenWebUI_Tailscale_AutoStart",
    [string]$VerifyTaskName = "ManaOS_OpenWebUI_Verify_OnLogon",
    [int]$VerifyDelaySeconds = 180,
    [string]$WebhookUrl = "",
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "generic",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess
)

$ErrorActionPreference = "Stop"

function Write-Step($text) {
    Write-Host "`n== $text ==" -ForegroundColor Cyan
}

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

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @("generic", "slack", "discord")) {
            $resolvedFormat = $envFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRaw -in @("1", "true", "yes", "on"))
    }

    return [ordered]@{
        webhook_url = $resolvedUrl
        webhook_format = $resolvedFormat
        webhook_mention = $resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
    }
}

function Invoke-PowerShellFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [hashtable]$Params = @{}
    )

    $cmd = @("-ExecutionPolicy", "Bypass", "-File", $ScriptPath)
    foreach ($k in $Params.Keys) {
        $v = $Params[$k]
        if ($v -is [switch]) {
            if ($v.IsPresent) { $cmd += "-$k" }
        }
        elseif ($v -is [bool]) {
            if ($v) { $cmd += "-$k" }
        }
        elseif ($null -ne $v -and -not [string]::IsNullOrWhiteSpace([string]$v)) {
            $cmd += "-$k"
            $cmd += [string]$v
        }
    }

    & powershell @cmd
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: $ScriptPath"
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptRoot "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$startScript = Join-Path $scriptRoot "start_openwebui_tailscale.ps1"
$registerScript = Join-Path $scriptRoot "register_openwebui_verify_autorun.ps1"
$verifyScript = Join-Path $scriptRoot "verify_openwebui_autostart.ps1"

if (-not (Test-Path $startScript)) { throw "Missing script: $startScript" }
if (-not (Test-Path $registerScript)) { throw "Missing script: $registerScript" }
if (-not (Test-Path $verifyScript)) { throw "Missing script: $verifyScript" }

Write-Host "Finalize OpenWebUI autostart workflow" -ForegroundColor Green

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

Write-Step "Ensure Main Autostart"
Invoke-PowerShellFile -ScriptPath $startScript -Params @{
    EnsureStartupTask = $true
    StartupTaskName = $StartupTaskName
    SkipServe = $true
    WebhookUrl = $WebhookUrl
}

Write-Step "Register Verify Autorun"
Invoke-PowerShellFile -ScriptPath $registerScript -Params @{
    TaskName = $VerifyTaskName
    DelaySeconds = $VerifyDelaySeconds
    RunNow = $true
    WebhookUrl = $WebhookUrl
    WebhookFormat = $WebhookFormat
    WebhookMention = $WebhookMention
    NotifyOnSuccess = [bool]$NotifyOnSuccess
}

Write-Step "Startup-Path Simulation"
Invoke-PowerShellFile -ScriptPath $startScript -Params @{
    InvocationSource = "startup_run_key"
    WebhookUrl = $WebhookUrl
}

Write-Step "Strict Verification"
$verifyLog = Join-Path $logsDir "verify_openwebui_autostart_last.log"
$verifyParams = @{
    RequireStartupSource = $true
    WebhookUrl = $WebhookUrl
    WebhookFormat = $WebhookFormat
    WebhookMention = $WebhookMention
    NotifyOnSuccess = [bool]$NotifyOnSuccess
}

$cmd = @("-ExecutionPolicy", "Bypass", "-File", $verifyScript)
foreach ($k in $verifyParams.Keys) {
    $v = $verifyParams[$k]
    if ($v -is [bool]) {
        if ($v) { $cmd += "-$k" }
    }
    elseif ($null -ne $v -and -not [string]::IsNullOrWhiteSpace([string]$v)) {
        $cmd += "-$k"
        $cmd += [string]$v
    }
}

& powershell @cmd *> $verifyLog
if ($LASTEXITCODE -ne 0) {
    Get-Content $verifyLog -Tail 100
    throw "Strict verification failed"
}

$state = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    startup_task_name = $StartupTaskName
    verify_task_name = $VerifyTaskName
    verify_delay_seconds = $VerifyDelaySeconds
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    notify_on_success = [bool]$NotifyOnSuccess
    verify_log = $verifyLog
    result = "ok"
}

$statePath = Join-Path $logsDir "finalize_openwebui_autostart_status.json"
$state | ConvertTo-Json -Depth 6 | Set-Content -Path $statePath -Encoding UTF8

Write-Host "" 
Write-Host "[OK] Finalize completed" -ForegroundColor Green
Write-Host "[OK] Status: $statePath" -ForegroundColor Green
Write-Host "[OK] Verify log: $verifyLog" -ForegroundColor Green
