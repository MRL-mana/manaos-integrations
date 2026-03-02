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
$v2Script = Join-Path $scriptDir "install_image_pipeline_probe_task_v2.ps1"

if (-not (Test-Path $v2Script)) {
    throw "v2 installer script not found: $v2Script"
}

$invokeArgs = @{
    TaskName = $TaskName
    IntervalMinutes = $IntervalMinutes
    UnifiedApiUrl = $UnifiedApiUrl
    ComfyUiUrl = $ComfyUiUrl
    WebhookFormat = $WebhookFormat
    NotifyCooldownMinutes = $NotifyCooldownMinutes
    RunLevel = $RunLevel
}

if (-not [string]::IsNullOrWhiteSpace($LogFile)) { $invokeArgs.LogFile = $LogFile }
if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) { $invokeArgs.WebhookUrl = $WebhookUrl }
if (-not [string]::IsNullOrWhiteSpace($WebhookMention)) { $invokeArgs.WebhookMention = $WebhookMention }
if (-not [string]::IsNullOrWhiteSpace($NotifyStateFile)) { $invokeArgs.NotifyStateFile = $NotifyStateFile }

if ($NotifyOnSuccess) { $invokeArgs.NotifyOnSuccess = $true }
if ($RunAsSystem) { $invokeArgs.RunAsSystem = $true }
if ($NoFallbackToCurrentUser) { $invokeArgs.NoFallbackToCurrentUser = $true }
if ($NoFallbackToLimited) { $invokeArgs.NoFallbackToLimited = $true }
if ($RunNow) { $invokeArgs.RunNow = $true }
if ($PrintOnly) { $invokeArgs.PrintOnly = $true }

& $v2Script @invokeArgs
exit $LASTEXITCODE
