param(
    [switch]$RequireWebhook,
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Name)
    $v = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    return [Environment]::GetEnvironmentVariable($Name, "User")
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptDir "logs"
$timestampTag = Get-Date -Format "yyyyMMdd_HHmmss"
$verifyLatestPath = Join-Path $logsDir "daily_health_notify_verify_latest.json"
$verifyReportPath = Join-Path $logsDir ("daily_health_notify_verify_" + $timestampTag + ".json")
$verifyHistoryPath = Join-Path $logsDir "daily_health_notify_verify_history.jsonl"
$latestReportPath = Join-Path $scriptDir "logs\daily_health_smoke_latest.json"

New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$result = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    checks = [ordered]@{}
}

$taskName = "ManaOS_Daily_Health_Smoke"
try {
    schtasks /Query /TN $taskName /FO LIST 2>&1 | Out-Null
    $taskOk = ($LASTEXITCODE -eq 0)
    $result.checks.task_registered = [ordered]@{ ok = $taskOk; detail = if ($taskOk) { "$taskName exists" } else { "$taskName missing" } }
}
catch {
    $result.checks.task_registered = [ordered]@{ ok = $false; detail = $_.Exception.Message }
}

$webhookUrl = [string](Get-EnvValue -Name "MANAOS_WEBHOOK_URL")
$webhookFormat = [string](Get-EnvValue -Name "MANAOS_WEBHOOK_FORMAT")
$notifyOnSuccess = [string](Get-EnvValue -Name "MANAOS_NOTIFY_ON_SUCCESS")

$hasWebhook = -not [string]::IsNullOrWhiteSpace($webhookUrl)
$envOk = if ($RequireWebhook) { $hasWebhook } else { $true }
$envDetail = if ($hasWebhook) {
    "webhook configured"
}
elseif ($RequireWebhook) {
    "MANAOS_WEBHOOK_URL missing"
}
else {
    "webhook not configured (optional)"
}

$result.checks.notify_env = [ordered]@{
    ok = $envOk
    detail = $envDetail
    webhook_enabled = $hasWebhook
    webhook_format = $webhookFormat
    notify_on_success_raw = $notifyOnSuccess
}

if (Test-Path $latestReportPath) {
    try {
        $latest = Get-Content -Path $latestReportPath -Raw | ConvertFrom-Json
        $reportOk = ($null -ne $latest.overall_ok) -and ($null -ne $latest.notify)
        $result.checks.latest_report = [ordered]@{
            ok = $reportOk
            detail = if ($reportOk) { "latest report parsed" } else { "latest report missing overall_ok/notify" }
            path = $latestReportPath
            overall_ok = $latest.overall_ok
            notify = $latest.notify
        }
    }
    catch {
        $result.checks.latest_report = [ordered]@{
            ok = $false
            detail = "failed to parse latest report: $($_.Exception.Message)"
            path = $latestReportPath
        }
    }
}
else {
    $result.checks.latest_report = [ordered]@{
        ok = $false
        detail = "latest report file not found"
        path = $latestReportPath
    }
}

$overall = $true
foreach ($k in $result.checks.Keys) {
    if (-not [bool]$result.checks[$k].ok) {
        $overall = $false
        break
    }
}

$result.overall_ok = $overall

$json = $result | ConvertTo-Json -Depth 8
$json | Set-Content -Path $verifyLatestPath -Encoding UTF8
$json | Set-Content -Path $verifyReportPath -Encoding UTF8
($result | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $verifyHistoryPath -Encoding UTF8

$result.paths = [ordered]@{
    verify_latest = $verifyLatestPath
    verify_report = $verifyReportPath
    verify_history = $verifyHistoryPath
}

if ($AsJson) {
    $result | ConvertTo-Json -Depth 8
}
else {
    Write-Host "=== Daily Health Notify Setup Verify ===" -ForegroundColor Cyan
    foreach ($k in $result.checks.Keys) {
        $ok = [bool]$result.checks[$k].ok
        $detail = [string]$result.checks[$k].detail
        if ($ok) {
            Write-Host "[OK] $k - $detail" -ForegroundColor Green
        }
        else {
            Write-Host "[NG] $k - $detail" -ForegroundColor Red
        }
    }
    if ($overall) {
        Write-Host "Verify result: OK" -ForegroundColor Green
    }
    else {
        Write-Host "Verify result: NG" -ForegroundColor Red
    }
}

if ($overall) { exit 0 }
exit 1