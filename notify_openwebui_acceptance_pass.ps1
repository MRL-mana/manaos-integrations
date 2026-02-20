param(
    [string]$ReportDir = "",
    [switch]$WriteStatusFile,
    [ValidateSet("", "PASS", "FAIL", "UNKNOWN", "PENDING")]
    [string]$ForceVerdict = "",
    [string]$Reason = "",
    [switch]$SendWebhook
)

$ErrorActionPreference = "Stop"

function Resolve-NotifySettings {
    $resolvedUrl = $env:MANAOS_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
        $resolvedUrl = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")
    }

    $resolvedFormat = "discord"
    $envFormat = $env:MANAOS_WEBHOOK_FORMAT
    if ([string]::IsNullOrWhiteSpace($envFormat)) {
        $envFormat = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User")
    }
    if (-not [string]::IsNullOrWhiteSpace($envFormat)) {
        $fmt = $envFormat.Trim().ToLowerInvariant()
        if ($fmt -in @("generic", "slack", "discord")) {
            $resolvedFormat = $fmt
        }
    }

    $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    if ([string]::IsNullOrWhiteSpace($resolvedMention)) {
        $resolvedMention = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", "User")
    }

    $notifyOnSuccess = $false
    $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS
    if ([string]::IsNullOrWhiteSpace($notifyRaw)) {
        $notifyRaw = [Environment]::GetEnvironmentVariable("MANAOS_NOTIFY_ON_SUCCESS", "User")
    }
    if (-not [string]::IsNullOrWhiteSpace($notifyRaw)) {
        $notifyOnSuccess = ($notifyRaw.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on"))
    }

    return [ordered]@{
        webhook_url = $resolvedUrl
        webhook_format = $resolvedFormat
        webhook_mention = $resolvedMention
        notify_on_success = [bool]$notifyOnSuccess
    }
}

function Send-AcceptanceWebhook {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Verdict,
        [Parameter(Mandatory = $true)]
        [string]$StatusLine,
        [string]$InReason = ""
    )

    $notify = Resolve-NotifySettings
    $target = [string]$notify.webhook_url
    if ([string]::IsNullOrWhiteSpace($target)) {
        return
    }

    $shouldSend = ($Verdict -eq "FAIL" -or $Verdict -eq "UNKNOWN" -or $Verdict -eq "PENDING" -or [bool]$notify.notify_on_success)
    if (-not $shouldSend) {
        return
    }

    $summary = "OpenWebUI acceptance $Verdict | $StatusLine"
    if (-not [string]::IsNullOrWhiteSpace($InReason)) {
        $summary += " | reason=$InReason"
    }
    $mentionPrefix = if ([string]::IsNullOrWhiteSpace([string]$notify.webhook_mention)) { "" } else { ([string]$notify.webhook_mention + " ") }

    if ([string]$notify.webhook_format -eq "slack") {
        $payload = [ordered]@{ text = "$mentionPrefix$summary" }
    }
    elseif ([string]$notify.webhook_format -eq "discord") {
        $payload = [ordered]@{
            content = "$mentionPrefix$summary"
            embeds = @(
                [ordered]@{
                    title = "OpenWebUI Acceptance Verdict"
                    description = $summary
                    color = if ($Verdict -eq "PASS") { 5763719 } else { 15548997 }
                    timestamp = (Get-Date).ToString("o")
                }
            )
        }
    }
    else {
        $payload = [ordered]@{
            type = "openwebui_acceptance_verdict"
            verdict = $Verdict
            timestamp = (Get-Date).ToString("o")
            status_line = $StatusLine
            reason = $InReason
            summary = $summary
        }
    }

    try {
        Invoke-RestMethod -Uri $target -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 8) | Out-Null
        Write-Host "[INFO] Acceptance webhook notification sent." -ForegroundColor Gray
    }
    catch {
        Write-Host "[WARN] Acceptance webhook notification failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Resolve-OptionalDiagInfo {
    param(
        [string]$BaseDir
    )

    $diagPath = Join-Path $BaseDir "logs\optional_services_diag_latest.json"
    if (-not (Test-Path $diagPath)) {
        return [ordered]@{
            path = ""
            error = ""
        }
    }

    $diagError = ""
    try {
        $diagObj = Get-Content -Path $diagPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($diagObj -and $diagObj.error) {
            $diagError = [string]$diagObj.error
        }
    }
    catch {
        $diagError = ""
    }

    return [ordered]@{
        path = $diagPath
        error = $diagError
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ReportDir) {
    $ReportDir = Join-Path $scriptDir "Reports"
}

if (-not (Test-Path $ReportDir) -and [string]::IsNullOrWhiteSpace($ForceVerdict)) {
    Write-Host "[WARN] report_dir_missing status=UNKNOWN dir=$ReportDir" -ForegroundColor Yellow
    exit 0
}

$latest = $null
$summary = $null
$verdict = ""
$createdAt = ""

if (-not [string]::IsNullOrWhiteSpace($ForceVerdict)) {
    $verdict = $ForceVerdict
    $createdAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
}
else {
    $latest = Get-ChildItem -Path $ReportDir -Filter "OpenWebUI_Tool_Acceptance_Final_*.json" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        Write-Host "[WARN] acceptance_status=UNKNOWN reason=no_final_summary" -ForegroundColor Yellow
        if ($SendWebhook) {
            Send-AcceptanceWebhook -Verdict "UNKNOWN" -StatusLine "acceptance_status=UNKNOWN reason=no_final_summary" -InReason "no_final_summary"
        }
        exit 0
    }

    $summary = Get-Content -Path $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $verdict = [string]$summary.final_verdict
    $createdAt = [string]$summary.created_at
}
$fileName = if ($latest) { $latest.Name } else { "n/a" }
$diagInfo = Resolve-OptionalDiagInfo -BaseDir $scriptDir
$reasonFinal = [string]$Reason
if (($verdict -eq "FAIL" -or $verdict -eq "UNKNOWN" -or $verdict -eq "PENDING") -and (-not [string]::IsNullOrWhiteSpace([string]$diagInfo.path))) {
    if ([string]::IsNullOrWhiteSpace($reasonFinal)) {
        $reasonFinal = "diag_file=$($diagInfo.path)"
    }
    else {
        $reasonFinal += " diag_file=$($diagInfo.path)"
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$diagInfo.error)) {
        $diagErr = ([string]$diagInfo.error -replace "[\r\n]+", " ").Trim()
        if ($diagErr.Length -gt 220) {
            $diagErr = $diagErr.Substring(0, 220)
        }
        $reasonFinal += " diag_error=$diagErr"
    }
}

$statusLine = "acceptance_status=$verdict created_at=$createdAt file=$fileName"
if (-not [string]::IsNullOrWhiteSpace($reasonFinal)) {
    $statusLine += " reason=$reasonFinal"
}
if (-not [string]::IsNullOrWhiteSpace([string]$diagInfo.path)) {
    $statusLine += " diag_file=$($diagInfo.path)"
}

if ($WriteStatusFile) {
    if (-not (Test-Path $ReportDir)) {
        New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
    }
    $statusFile = Join-Path $ReportDir "OpenWebUI_Acceptance_Latest_Status.txt"
    Set-Content -Path $statusFile -Value $statusLine -Encoding UTF8
}

if ($SendWebhook) {
    Send-AcceptanceWebhook -Verdict $verdict -StatusLine $statusLine -InReason $reasonFinal
}

switch ($verdict) {
    "PASS" {
        Write-Host "[PASS] $statusLine" -ForegroundColor Green
        exit 0
    }
    "FAIL" {
        Write-Host "[INFO] $statusLine" -ForegroundColor Red
        exit 0
    }
    default {
        Write-Host "[INFO] $statusLine" -ForegroundColor Yellow
        exit 0
    }
}
