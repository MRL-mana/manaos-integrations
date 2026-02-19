param(
    [int]$MaxAgeMinutes = 30,
    [switch]$RequireStartupSource,
    [string]$WebhookUrl = "",
    [switch]$NotifyOnSuccess,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "generic",
    [string]$WebhookMention = ""
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERR] $msg" -ForegroundColor Red }

function Send-WebhookNotification {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Passed,
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Registration,
        [Parameter(Mandatory = $true)]
        [double]$AgeMinutes,
        [Parameter(Mandatory = $true)]
        [bool]$LocalOk,
        [Parameter(Mandatory = $true)]
        [bool]$IpOk,
        [Parameter(Mandatory = $true)]
        [bool]$HttpsOk,
        [Parameter(Mandatory = $true)]
        [bool]$ServeEnabled,
        [Parameter(Mandatory = $true)]
        [bool]$RequireStartupPath
    )

    $target = $WebhookUrl
    if ([string]::IsNullOrWhiteSpace($target)) {
        $target = $env:OPENWEBUI_VERIFY_WEBHOOK_URL
    }

    if ([string]::IsNullOrWhiteSpace($target)) {
        return
    }

    if ((-not $Passed) -or $NotifyOnSuccess) {
        $statusText = if ($Passed) { "PASS" } else { "FAIL" }
        $summary = "OpenWebUI verify $statusText | source=$Source | reg=$Registration | age=${AgeMinutes}m | local=$LocalOk ip=$IpOk https=$HttpsOk"
        $mentionPrefix = if ([string]::IsNullOrWhiteSpace($WebhookMention)) { "" } else { "$WebhookMention " }

        if ($WebhookFormat -eq "slack") {
            $payload = [ordered]@{
                text = "$mentionPrefix$summary"
            }
        }
        elseif ($WebhookFormat -eq "discord") {
            $payload = [ordered]@{
                content = "$mentionPrefix$summary"
                embeds = @(
                    [ordered]@{
                        title = "OpenWebUI Autostart Verify"
                        description = $summary
                        color = if ($Passed) { 5763719 } else { 15548997 }
                        timestamp = (Get-Date).ToString("o")
                    }
                )
            }
        }
        else {
            $payload = [ordered]@{
                type = if ($Passed) { "openwebui_verify_pass" } else { "openwebui_verify_fail" }
                passed = $Passed
                timestamp = (Get-Date).ToString("o")
                source = $Source
                startup_registration = $Registration
                age_minutes = $AgeMinutes
                checks = [ordered]@{
                    local_ok = $LocalOk
                    tailscale_ip_ok = $IpOk
                    tailscale_https_ok = $HttpsOk
                    serve_enabled = $ServeEnabled
                }
                require_startup_source = $RequireStartupPath
                summary = $summary
            }
        }

        try {
            Invoke-RestMethod -Uri $target -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 8) | Out-Null
            Write-Host "[INFO] Webhook notification sent." -ForegroundColor Gray
        }
        catch {
            Write-Warn "Webhook notification failed: $($_.Exception.Message)"
        }
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$statusPath = Join-Path $scriptRoot "logs\openwebui_tailscale_status.json"

Write-Host "Verify OpenWebUI autostart evidence" -ForegroundColor Cyan

if (-not (Test-Path $statusPath)) {
    Write-Err "Status file not found: $statusPath"
    exit 1
}

$status = Get-Content -Path $statusPath -Raw | ConvertFrom-Json

$timestamp = $null
try {
    $timestamp = [datetimeoffset]::Parse($status.timestamp)
}
catch {
    Write-Err "Invalid timestamp in status file"
    exit 1
}

$ageMin = [math]::Round(((Get-Date).ToUniversalTime() - $timestamp.UtcDateTime).TotalMinutes, 2)
if ($ageMin -le $MaxAgeMinutes) {
    Write-Ok "Status age ${ageMin}m (<= ${MaxAgeMinutes}m)"
    $ageOk = $true
}
else {
    Write-Warn "Status age ${ageMin}m (> ${MaxAgeMinutes}m)"
    $ageOk = $false
}

$localOk = ($status.checks.local_http_status -eq 200)
$ipOk = ($status.checks.tailscale_ip_http_status -eq 200)
$httpsOk = ($status.checks.tailscale_https_status -eq 200)
$serveEnabled = [bool]$status.serve_enabled

if ($localOk) { Write-Ok "Local health 200" } else { Write-Warn "Local health is not 200" }
if ($ipOk) { Write-Ok "Tailscale IP health 200" } else { Write-Warn "Tailscale IP health is not 200" }
if ($serveEnabled) {
    if ($httpsOk) { Write-Ok "Tailscale HTTPS health 200" } else { Write-Warn "Tailscale HTTPS health is not 200" }
}
else {
    Write-Warn "Serve is disabled"
}

$registration = [string]$status.startup_registration
$registrationOk = ($registration -in @("run_key", "scheduled_task"))
if ($registrationOk) {
    Write-Ok "Startup registration: $registration"
}
else {
    Write-Warn "Startup registration is not ready: $registration"
}

$source = [string]$status.invocation_source
$sourceOk = ($source -in @("startup_run_key", "startup_task"))
if ($RequireStartupSource) {
    if ($sourceOk) { Write-Ok "Invocation source is startup path: $source" }
    else { Write-Warn "Invocation source is not startup path: $source" }
}
else {
    Write-Host "[INFO] Invocation source: $source" -ForegroundColor Gray
}

$entryName = if ([string]::IsNullOrWhiteSpace([string]$status.startup_registration_detail)) {
    "ManaOS_OpenWebUI_Tailscale_AutoStart"
}
else {
    [string]$status.startup_registration_detail
}
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$runValue = $null
try {
    $runValue = (Get-ItemProperty -Path $runKey -Name $entryName -ErrorAction Stop).$entryName
}
catch {
}

if ([string]::IsNullOrWhiteSpace($runValue)) {
    Write-Warn "Run entry not found: $entryName"
    $runEntryOk = $false
}
else {
    Write-Ok "Run entry exists: $entryName"
    $runEntryOk = $true
}

$taskExists = $false
try {
    $null = Get-ScheduledTask -TaskName $entryName -ErrorAction Stop
    $taskExists = $true
}
catch {
}
if ($taskExists) {
    Write-Ok "Scheduled task exists: $entryName"
}
else {
    Write-Host "[INFO] Scheduled task not found (Run entry fallback may be in use)" -ForegroundColor Gray
}

$healthOk = $localOk -and $ipOk -and ((-not $serveEnabled) -or $httpsOk)
$baseOk = $ageOk -and $healthOk -and $registrationOk
$finalOk = if ($RequireStartupSource) { $baseOk -and $sourceOk } else { $baseOk }

Write-Host ""
if ($finalOk) {
    Send-WebhookNotification -Passed $true -Source $source -Registration $registration -AgeMinutes $ageMin -LocalOk $localOk -IpOk $ipOk -HttpsOk $httpsOk -ServeEnabled $serveEnabled -RequireStartupPath ([bool]$RequireStartupSource)
    Write-Ok "Autostart verification passed"
    exit 0
}
else {
    Send-WebhookNotification -Passed $false -Source $source -Registration $registration -AgeMinutes $ageMin -LocalOk $localOk -IpOk $ipOk -HttpsOk $httpsOk -ServeEnabled $serveEnabled -RequireStartupPath ([bool]$RequireStartupSource)
    Write-Err "Autostart verification failed"
    exit 1
}
