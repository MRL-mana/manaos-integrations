param(
    [string]$TaskName = "ManaOS_Image_Pipeline_Probe_5min",
    [int]$IntervalMinutes = 5,
    [string]$UnifiedApiUrl = "http://127.0.0.1:9502",
    [string]$ComfyUiUrl = "http://127.0.0.1:8188",
    [string]$LogFile = "",
    [string]$HistoryFile = "",
    [string]$StateFile = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [switch]$NotifyOnRecovery,
    [switch]$DisableNotifyOnPartial,
    [switch]$DisableNotifyOnDown,
    [switch]$DisableNotifyOnUnifiedDegraded,
    [int]$NotifyCooldownMinutes = 15,
    [int]$NotifyUnifiedDegradedAfter = 3,
    [int]$NotifyUnifiedDegradedCooldownMinutes = 60,
    [string]$NotifyStateFile = "",
    [switch]$EnableAutoRecovery,
    [switch]$DisableAutoRecovery,
    [int]$RecoverAfterConsecutiveDown = 3,
    [int]$RecoveryCooldownSec = 300,
    [string]$RecoveryCommand = "",
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
$taskScript = Join-Path $scriptDir "run_image_pipeline_probe_once_v2.ps1"
if (-not (Test-Path $taskScript)) { throw "Task wrapper script not found: $taskScript" }
if ($IntervalMinutes -lt 1 -or $IntervalMinutes -gt 1440) { throw "IntervalMinutes must be 1..1440" }
if ($RecoverAfterConsecutiveDown -lt 1) { throw "RecoverAfterConsecutiveDown must be >= 1" }
if ($RecoveryCooldownSec -lt 0) { throw "RecoveryCooldownSec must be >= 0" }
if ($NotifyUnifiedDegradedAfter -lt 1) { throw "NotifyUnifiedDegradedAfter must be >= 1" }
if ($NotifyUnifiedDegradedCooldownMinutes -lt 0) { throw "NotifyUnifiedDegradedCooldownMinutes must be >= 0" }

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) { $WebhookUrl = $env:MANAOS_WEBHOOK_URL }
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) { $WebhookMention = $env:MANAOS_WEBHOOK_MENTION }
if ($NotifyCooldownMinutes -lt 0) { $NotifyCooldownMinutes = 0 }

$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
if ([string]::IsNullOrWhiteSpace($LogFile)) { $LogFile = Join-Path $logDir "image_pipeline_probe.latest.json" }
if ([string]::IsNullOrWhiteSpace($HistoryFile)) { $HistoryFile = Join-Path $logDir "image_pipeline_probe.history.jsonl" }
if ([string]::IsNullOrWhiteSpace($StateFile)) { $StateFile = Join-Path $logDir "image_pipeline_probe.state.json" }
if ([string]::IsNullOrWhiteSpace($NotifyStateFile)) { $NotifyStateFile = Join-Path $logDir "image_pipeline_probe_notify_state.json" }

$effectiveEnableAutoRecovery = $true
if ($DisableAutoRecovery.IsPresent) {
    $effectiveEnableAutoRecovery = $false
}
elseif ($EnableAutoRecovery.IsPresent) {
    $effectiveEnableAutoRecovery = $true
}

$configPath = Join-Path $logDir "image_pipeline_probe_task.config.json"
$configObj = [ordered]@{
    unified_api_url = $UnifiedApiUrl
    comfyui_url = $ComfyUiUrl
    log_file = $LogFile
    history_file = $HistoryFile
    state_file = $StateFile
    webhook_format = $WebhookFormat
    webhook_url = $WebhookUrl
    webhook_mention = $WebhookMention
    notify_on_success = [bool]$NotifyOnSuccess
    notify_on_recovery = [bool]$NotifyOnRecovery
    notify_on_partial = -not [bool]$DisableNotifyOnPartial
    notify_on_down = -not [bool]$DisableNotifyOnDown
    notify_on_unified_degraded = -not [bool]$DisableNotifyOnUnifiedDegraded
    notify_cooldown_minutes = [int]$NotifyCooldownMinutes
    notify_unified_degraded_after = [int]$NotifyUnifiedDegradedAfter
    notify_unified_degraded_cooldown_minutes = [int]$NotifyUnifiedDegradedCooldownMinutes
    notify_state_file = $NotifyStateFile
    enable_auto_recovery = [bool]$effectiveEnableAutoRecovery
    enable_auto_recovery_on_unified_degraded = $true
    recover_after_consecutive_down = [int]$RecoverAfterConsecutiveDown
    recovery_cooldown_sec = [int]$RecoveryCooldownSec
    recovery_command = [string]$RecoveryCommand
}
$configObj | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8

$taskRun = "pwsh -NoP -EP Bypass -File `"$taskScript`""
$effectiveRunLevel = $RunLevel
$useSystemAccount = $RunAsSystem.IsPresent
if ($RunAsSystem.IsPresent -and $effectiveRunLevel -eq 'LIMITED') { $effectiveRunLevel = 'HIGHEST' }

Write-Host "=== Register Image Pipeline Probe Task (v2) ===" -ForegroundColor Cyan
Write-Host "TaskName : $TaskName" -ForegroundColor Gray
Write-Host "Schedule : MINUTE /MO $IntervalMinutes" -ForegroundColor Gray
Write-Host "RunLevel : $effectiveRunLevel" -ForegroundColor Gray
Write-Host "Config   : $configPath" -ForegroundColor Gray
Write-Host "History  : $HistoryFile" -ForegroundColor Gray
Write-Host "State    : $StateFile" -ForegroundColor Gray
Write-Host "Recovery : $(if ($effectiveEnableAutoRecovery) { 'enabled' } else { 'disabled' })" -ForegroundColor Gray
Write-Host "Degraded : enabled=$(if ($DisableNotifyOnUnifiedDegraded) { 'false' } else { 'true' }), after=$NotifyUnifiedDegradedAfter, cooldown=${NotifyUnifiedDegradedCooldownMinutes}min" -ForegroundColor Gray
Write-Host "Command  : $taskRun" -ForegroundColor DarkGray
if ($PrintOnly) { Write-Host "[INFO] PrintOnly mode: no task registration" -ForegroundColor Yellow; exit 0 }

$createTask = {
    param([string]$Level)
    $args = @('/Create','/SC','MINUTE','/MO',"$IntervalMinutes",'/TN',$TaskName,'/TR',$taskRun,'/RL',$Level,'/F')
    if ($useSystemAccount) { $args += @('/RU','SYSTEM') }
    schtasks @args | Out-Null
    return $LASTEXITCODE
}

$exitCode = & $createTask $effectiveRunLevel
if ($exitCode -ne 0 -and $useSystemAccount -and -not $NoFallbackToCurrentUser) {
    $useSystemAccount = $false
    if ($effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited) { $effectiveRunLevel = 'LIMITED' }
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0 -and $effectiveRunLevel -eq 'HIGHEST' -and -not $NoFallbackToLimited -and -not $useSystemAccount) {
    $effectiveRunLevel = 'LIMITED'
    $exitCode = & $createTask $effectiveRunLevel
}
if ($exitCode -ne 0) { throw "Failed to create scheduled task (exit=$exitCode)" }

Write-Host "[OK] Scheduled task created: $TaskName" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST
if ($RunNow) { schtasks /Run /TN $TaskName | Out-Null; Write-Host "[OK] Scheduled task triggered: $TaskName" -ForegroundColor Green }
