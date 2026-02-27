param(
    [string]$TaskName = "ManaOS_OpenWebUI_Tailscale_Watch_5min",
    [string]$ConfigFile = "",
    [string]$BaseUrl = "",
    [string]$LogPath = "",
    [string]$JsonOutFile = "",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [int]$NotifyFailureCooldownMinutes = 15,
    [string]$NotifyStateFile = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ConfigFile)) {
    $ConfigFile = Join-Path $scriptDir "logs\openwebui_tailscale_watch_task.config.json"
}

if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content -Path $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.task_name) { $TaskName = [string]$cfg.task_name }
        if ($cfg.base_url) { $BaseUrl = [string]$cfg.base_url }
        if ($cfg.log_path) { $LogPath = [string]$cfg.log_path }
        if ($cfg.json_out_file) { $JsonOutFile = [string]$cfg.json_out_file }
        if ($cfg.webhook_format) { $WebhookFormat = [string]$cfg.webhook_format }
        if ($cfg.webhook_url) { $WebhookUrl = [string]$cfg.webhook_url }
        if ($cfg.webhook_mention) { $WebhookMention = [string]$cfg.webhook_mention }
        if ($null -ne $cfg.notify_failure_cooldown_minutes) { $NotifyFailureCooldownMinutes = [int]$cfg.notify_failure_cooldown_minutes }
        if ($cfg.notify_state_file) { $NotifyStateFile = [string]$cfg.notify_state_file }
    }
    catch {
        Write-Host "[WARN] Failed to parse config file: $ConfigFile" -ForegroundColor Yellow
    }
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if ([string]::IsNullOrWhiteSpace($NotifyStateFile)) {
    $NotifyStateFile = Join-Path $scriptDir "logs\openwebui_tailscale_watch_notify_state.json"
}
if ($NotifyFailureCooldownMinutes -lt 0) {
    $NotifyFailureCooldownMinutes = 0
}

function Ensure-ParentDir {
    param([string]$Path)
    $dir = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

function Load-NotifyState {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return [pscustomobject]@{
            last_failure_notified_at = ''
            last_status = ''
        }
    }

    try {
        return Get-Content -Path $Path -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            last_failure_notified_at = ''
            last_status = ''
        }
    }
}

function Save-NotifyState {
    param(
        [string]$Path,
        [string]$LastFailureNotifiedAt,
        [string]$LastStatus
    )

    Ensure-ParentDir -Path $Path
    $obj = [ordered]@{
        last_failure_notified_at = $LastFailureNotifiedAt
        last_status = $LastStatus
        updated_at = [datetimeoffset]::Now.ToString('o')
    }
    ($obj | ConvertTo-Json -Depth 4) | Set-Content -Path $Path -Encoding UTF8
}

function Send-WebhookNotification {
    param(
        [string]$Url,
        [ValidateSet('generic','slack','discord')]
        [string]$Format,
        [string]$Status,
        [string]$Title,
        [string]$Body,
        [string]$Mention = ''
    )

    if ([string]::IsNullOrWhiteSpace($Url)) { return }

    $content = if ([string]::IsNullOrWhiteSpace($Mention)) { "$Title`n$Body" } else { "$Mention $Title`n$Body" }
    if ($Format -eq 'discord') {
        $payload = @{ content = $content }
    }
    elseif ($Format -eq 'slack') {
        $payload = @{ text = $content }
    }
    else {
        $payload = @{ status = $Status; title = $Title; body = $Body; mention = $Mention }
    }

    try {
        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 8) | Out-Null
        Write-Host "[OK] Webhook notified ($Status)" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Webhook notify failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Write-WatchOutput {
    param(
        [object]$Payload,
        [string]$LogPath,
        [string]$JsonOutFile
    )

    $line = $Payload | ConvertTo-Json -Compress -Depth 8
    Add-Content -Path $LogPath -Value $line -Encoding UTF8

    if (-not [string]::IsNullOrWhiteSpace($JsonOutFile)) {
        $jsonDir = Split-Path -Parent $JsonOutFile
        if (-not [string]::IsNullOrWhiteSpace($jsonDir) -and -not (Test-Path $jsonDir)) {
            New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
        }
        ($Payload | ConvertTo-Json -Depth 8) | Set-Content -Path $JsonOutFile -Encoding UTF8
    }
}

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    if (-not [string]::IsNullOrWhiteSpace($env:OPENWEBUI_URL)) {
        $BaseUrl = $env:OPENWEBUI_URL.TrimEnd('/')
    }
    else {
        $BaseUrl = "http://127.0.0.1:3001"
    }
}

if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path $scriptDir "logs\openwebui_tailscale_watch_task.jsonl"
}

$logDir = Split-Path -Parent $LogPath
if (-not [string]::IsNullOrWhiteSpace($logDir) -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
Ensure-ParentDir -Path $NotifyStateFile

$openwebuiOk = $false
$openwebuiStatusCode = $null
$openwebuiError = $null

try {
    $response = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $openwebuiStatusCode = [int]$response.StatusCode
    $openwebuiOk = ($openwebuiStatusCode -ge 200 -and $openwebuiStatusCode -lt 500)
}
catch {
    $openwebuiError = $_.Exception.Message
}

$tailscaleIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue |
    Sort-Object -Property InterfaceMetric, SkipAsSource |
    Select-Object -First 1 -ExpandProperty IPAddress

$portCheck = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
$portListening = ($null -ne $portCheck)

$firewallRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    ($_.DisplayName -like "*3001*") -or
    ($_.DisplayName -like "*Open WebUI*") -or
    ($_.DisplayName -like "*OpenWebUI*")
}
$firewallRuleCount = @($firewallRules).Count

$issues = New-Object System.Collections.Generic.List[string]
if (-not $openwebuiOk) {
    if ([string]::IsNullOrWhiteSpace($openwebuiError)) {
        $issues.Add("OpenWebUI check failed")
    }
    else {
        $issues.Add("OpenWebUI check failed: $openwebuiError")
    }
}
if ([string]::IsNullOrWhiteSpace($tailscaleIp)) {
    $issues.Add("Tailscale IP not found")
}
if (-not $portListening) {
    $issues.Add("Port 3001 is not listening")
}

$ok = ($issues.Count -eq 0)

$notifyState = Load-NotifyState -Path $NotifyStateFile
$lastFailureNotifiedAt = [string]$notifyState.last_failure_notified_at
$lastFailureNotifiedDt = $null
if (-not [string]::IsNullOrWhiteSpace($lastFailureNotifiedAt)) {
    try { $lastFailureNotifiedDt = [datetimeoffset]::Parse($lastFailureNotifiedAt) } catch { $lastFailureNotifiedDt = $null }
}

$failureNotified = $false
$failureNotifySuppressedReason = ''
$failureNotifyAttempted = $false
$now = [datetimeoffset]::Now

$payload = [ordered]@{
    ts = $now.ToString("o")
    task = $TaskName
    base_url = $BaseUrl
    ok = $ok
    openwebui_ok = $openwebuiOk
    openwebui_status_code = $openwebuiStatusCode
    tailscale_ip = $tailscaleIp
    port_3001_listening = $portListening
    firewall_rule_count = $firewallRuleCount
    notify_failure_cooldown_minutes = $NotifyFailureCooldownMinutes
    failure_notify_attempted = $false
    failure_notified = $false
    failure_notify_suppressed_reason = ''
    issues = @($issues)
}

if ($ok) {
    $payload.failure_notify_attempted = $false
    $payload.failure_notified = $false
    $payload.failure_notify_suppressed_reason = 'not_failure_path'
    Write-WatchOutput -Payload $payload -LogPath $LogPath -JsonOutFile $JsonOutFile

    $msg = "[OK] OpenWebUI/Tailscale watch healthy"
    if ($openwebuiStatusCode) { $msg += " | status=$openwebuiStatusCode" }
    if ($tailscaleIp) { $msg += " | ip=$tailscaleIp" }
    Write-Host $msg -ForegroundColor Green
    Save-NotifyState -Path $NotifyStateFile -LastFailureNotifiedAt $lastFailureNotifiedAt -LastStatus 'success'
    exit 0
}

Write-Host "[ALERT] OpenWebUI/Tailscale watch issues detected" -ForegroundColor Red
foreach ($issue in $issues) {
    Write-Host " - $issue" -ForegroundColor Red
}

if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
    $failureNotifyAttempted = $true
    $shouldNotifyFailure = $false
    $elapsedMinutes = $null
    if ($null -eq $lastFailureNotifiedDt) {
        $shouldNotifyFailure = $true
    }
    else {
        $elapsedMinutes = ([datetimeoffset]::Now - $lastFailureNotifiedDt).TotalMinutes
    }

    if (-not $shouldNotifyFailure -and $elapsedMinutes -ge $NotifyFailureCooldownMinutes) {
        $shouldNotifyFailure = $true
    }
    elseif (-not $shouldNotifyFailure) {
        $remainingCooldown = [math]::Ceiling($NotifyFailureCooldownMinutes - $elapsedMinutes)
        $failureNotifySuppressedReason = "cooldown(${remainingCooldown}m_remaining)"
    }

    if ($shouldNotifyFailure) {
        $body = "base_url=$BaseUrl issues=$([string]::Join('; ', @($issues)))"
        Send-WebhookNotification -Url $WebhookUrl -Format $WebhookFormat -Status 'failure' -Title '[OpenWebUI Watch] FAILURE' -Body $body -Mention $WebhookMention
        $lastFailureNotifiedAt = [datetimeoffset]::Now.ToString('o')
        $failureNotified = $true
        $failureNotifySuppressedReason = ''
        Write-Host "[INFO] Failure webhook sent" -ForegroundColor Yellow
    }
    else {
        Write-Host "[INFO] Failure webhook suppressed: $failureNotifySuppressedReason" -ForegroundColor DarkGray
    }
}
else {
    $failureNotifyAttempted = $false
    $failureNotifySuppressedReason = 'webhook_not_configured'
    Write-Host "[INFO] Failure webhook suppressed: webhook not configured" -ForegroundColor DarkGray
}

if (-not $failureNotified -and [string]::IsNullOrWhiteSpace($failureNotifySuppressedReason) -and $failureNotifyAttempted) {
    $failureNotifySuppressedReason = 'not_triggered'
    Write-Host "[INFO] Failure webhook suppressed: not triggered" -ForegroundColor DarkGray
}

$payload.failure_notify_attempted = $failureNotifyAttempted
$payload.failure_notified = $failureNotified
$payload.failure_notify_suppressed_reason = $failureNotifySuppressedReason
Write-WatchOutput -Payload $payload -LogPath $LogPath -JsonOutFile $JsonOutFile

Save-NotifyState -Path $NotifyStateFile -LastFailureNotifiedAt $lastFailureNotifiedAt -LastStatus 'failure'
exit 1
