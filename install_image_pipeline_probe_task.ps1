param(
    [string]$TaskName = "ManaOS_Image_Pipeline_Probe_5min",
    [int]$IntervalMinutes = 5,
    [string]$UnifiedApiUrl = "http://127.0.0.1:9502",
    [string]$ComfyUiUrl = "http://127.0.0.1:8188",
    [string]$LogFile = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [int]$NotifyCooldownMinutes = 15,
    [string]$NotifyStateFile = "",
    [ValidateSet('LIMITED','HIGHEST')]
    [string]$RunLevel = 'LIMITED',
    [switch]$RunAsSystem,
    [switch]$NoFallbackToCurrentUser,
    [switch]$NoFallbackToLimited,
    [switch]$RunNow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$probeScript = Join-Path $scriptDir "monitor_image_pipeline.ps1"
$taskScript = Join-Path $scriptDir "run_image_pipeline_probe_once.ps1"

if (-not (Test-Path $probeScript)) {
    throw "Probe script not found: $probeScript"
}
if (-not (Test-Path $taskScript)) {
    throw "Task wrapper script not found: $taskScript"
}

if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) {
    throw "IntervalMinutes must be 1..1440"
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if (-not $NotifyOnSuccess.IsPresent -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
    $raw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
    if ($raw -in @('1','true','yes','on')) {
        $NotifyOnSuccess = $true
    }
}
if ($NotifyCooldownMinutes -lt 0) {
    $NotifyCooldownMinutes = 0
}
if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_COOLDOWN_MINUTES)) {
    try {
        $NotifyCooldownMinutes = [int]$env:MANAOS_NOTIFY_COOLDOWN_MINUTES
    }
    catch {
        Write-Host "[WARN] Invalid MANAOS_NOTIFY_COOLDOWN_MINUTES: $($env:MANAOS_NOTIFY_COOLDOWN_MINUTES)" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($LogFile)) {
    $logDir = Join-Path $scriptDir "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $LogFile = Join-Path $logDir "image_pipeline_probe.latest.json"
}

if ([string]::IsNullOrWhiteSpace($NotifyStateFile)) {
    $NotifyStateFile = Join-Path (Join-Path $scriptDir "logs") "image_pipeline_probe_notify_state.json"
}

$configPath = Join-Path $scriptDir "logs\image_pipeline_probe_task.config.json"
$configObj = [ordered]@{
    unified_api_url = $UnifiedApiUrl
    comfyui_url = $ComfyUiUrl
    log_file = $LogFile
    webhook_format = $WebhookFormat
    webhook_url = $WebhookUrl
    webhook_mention = $WebhookMention
    notify_on_success = [bool]$NotifyOnSuccess
    notify_cooldown_minutes = [int]$NotifyCooldownMinutes
    notify_state_file = $NotifyStateFile
}
$configObj | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8

$taskRun = "pwsh -NoP -EP Bypass -File `"$taskScript`""

$effectiveRunLevel = $RunLevel
$useSystemAccount = $RunAsSystem.IsPresent
if ($RunAsSystem.IsPresent -and $effectiveRunLevel -eq 'LIMITED') {
    $effectiveRunLevel = 'HIGHEST'
}

Write-Host "=== Register Image Pipeline Probe Task ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $effectiveRunLevel" -ForegroundColor Gray
Write-Host "Account  : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Gray
Write-Host "Probe    : $probeScript" -ForegroundColor Gray
Write-Host "TaskRun  : $taskScript" -ForegroundColor Gray
Write-Host "Config   : $configPath" -ForegroundColor Gray
Write-Host "LogFile  : $LogFile" -ForegroundColor Gray
Write-Host "Webhook  : $(if ([string]::IsNullOrWhiteSpace($WebhookUrl)) { 'disabled' } else { "$WebhookFormat ($WebhookUrl)" })" -ForegroundColor Gray
Write-Host "Cooldown : $NotifyCooldownMinutes min" -ForegroundColor Gray
Write-Host "State    : $NotifyStateFile" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray

if ($PrintOnly) {
    Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow
    exit 0
}

$createTask = {
    param([string]$Level)
    $args = @('/Create', '/SC', 'MINUTE', '/MO', "$IntervalMinutes", '/TN', $TaskName, '/TR', $taskRun, '/RL', $Level, '/F')
    if ($useSystemAccount) {
        $args += @('/RU', 'SYSTEM')
    }
    schtasks @args | Out-Null
    return $LASTEXITCODE
}

$exitCode = & $createTask $effectiveRunLevel
if ($exitCode -ne 0 -and $useSystemAccount -and -not $NoFallbackToCurrentUser) {
    Write-Host "[WARN] SYSTEM registration failed. retry with current user..." -ForegroundColor Yellow
    $useSystemAccount = $false
    if ($effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) {
        $effectiveRunLevel = 'LIMITED'
    }
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0 -and $effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited -and -not $useSystemAccount) {
    Write-Host "[WARN] HIGHEST registration failed. retry with LIMITED..." -ForegroundColor Yellow
    $effectiveRunLevel = 'LIMITED'
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0) {
    throw "Failed to create scheduled task (exit=$exitCode)"
}

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
Write-Host "[OK] Effective RunLevel: $effectiveRunLevel" -ForegroundColor Green
Write-Host "[OK] Effective Account : $(if ($useSystemAccount) { 'SYSTEM' } else { $env:USERNAME })" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green
}
