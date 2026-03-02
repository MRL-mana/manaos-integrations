param(
    [string]$Distro = "Ubuntu-22.04",
    [string]$ApiBaseUrl = "http://127.0.0.1:9502",
    [string]$ReadonlyApiKey = "ci-readonly-key",
    [ValidateSet('generic','slack','discord')]
    [string]$WebhookFormat = "discord",
    [string]$WebhookUrl = "",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess,
    [int]$RecoveryTimeoutSec = 120,
    [switch]$Recover,
    [switch]$StrictApi,
    [switch]$SkipWslDockerCheck,
    [switch]$SkipApiChecks,
    [switch]$SkipCiChecks
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptDir "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $logsDir ("daily_health_smoke_" + $timestamp + ".json")
$latestPath = Join-Path $logsDir "daily_health_smoke_latest.json"

$results = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    distro = $Distro
    api_base_url = $ApiBaseUrl
    checks = [ordered]@{}
}

function Add-CheckResult {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail
    )

    $results.checks[$Name] = [ordered]@{
        ok = $Ok
        detail = $Detail
    }

    if ($Ok) {
        Write-Host "[OK] $Name - $Detail" -ForegroundColor Green
    }
    else {
        Write-Host "[NG] $Name - $Detail" -ForegroundColor Red
    }
}

function Add-WarnResult {
    param(
        [string]$Name,
        [string]$Detail
    )

    $results.checks[$Name] = [ordered]@{
        ok = $true
        warning = $true
        detail = $Detail
    }

    Write-Host "[WARN] $Name - $Detail" -ForegroundColor Yellow
}

function Send-WebhookMessage {
    param(
        [string]$Url,
        [string]$Format,
        [string]$Message,
        [string]$Mention
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $false
    }

    $text = if ([string]::IsNullOrWhiteSpace($Mention)) { $Message } else { "$Mention`n$Message" }
    $fmt = if ([string]::IsNullOrWhiteSpace($Format)) { 'discord' } else { $Format.Trim().ToLowerInvariant() }
    $payload = switch ($fmt) {
        'slack' { @{ text = $text } }
        'generic' { @{ text = $text } }
        default { @{ content = $text } }
    }

    try {
        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 6) | Out-Null
        return $true
    }
    catch {
        Write-Host "[WARN] Failed to send webhook: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

function Get-LatestCompletedRun {
    param([string]$WorkflowName)

    try {
        $env:GITHUB_TOKEN = $null
        $env:GH_PAGER = "cat"
        $json = gh run list --workflow $WorkflowName --limit 10 --json databaseId,displayTitle,status,conclusion,url,createdAt 2>$null
        if ([string]::IsNullOrWhiteSpace($json)) {
            return $null
        }

        $runs = $json | ConvertFrom-Json
        return ($runs | Where-Object { $_.status -eq "completed" } | Select-Object -First 1)
    }
    catch {
        return $null
    }
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
    $WebhookUrl = $env:MANAOS_WEBHOOK_URL
}
if ([string]::IsNullOrWhiteSpace($WebhookMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
    $WebhookMention = $env:MANAOS_WEBHOOK_MENTION
}
if (-not $PSBoundParameters.ContainsKey('WebhookFormat') -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
    $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
    if ($envFormat -in @('generic', 'slack', 'discord')) {
        $WebhookFormat = $envFormat
    }
}
if (-not $NotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
    $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
    if ($notifyRaw -in @('1', 'true', 'yes', 'on', 'enabled')) {
        $NotifyOnSuccess = $true
    }
}

Write-Host "=== Daily Health Smoke ===" -ForegroundColor Cyan

if (-not $SkipWslDockerCheck) {
    $wslTaskName = "ManaOS_WSL_Docker_Health"
    try {
        schtasks /Query /TN $wslTaskName /FO LIST 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Add-CheckResult -Name "wsl_task_registered" -Ok $true -Detail "$wslTaskName exists"
        }
        else {
            Add-CheckResult -Name "wsl_task_registered" -Ok $false -Detail "$wslTaskName missing"
        }
    }
    catch {
        Add-CheckResult -Name "wsl_task_registered" -Ok $false -Detail $_.Exception.Message
    }

    try {
        $wslScript = Join-Path $scriptDir "check_wsl_docker_health.ps1"
        if (-not (Test-Path $wslScript)) {
            throw "script missing: $wslScript"
        }

        $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $wslScript, "-Distro", $Distro, "-TimeoutSec", "$RecoveryTimeoutSec")
        if ($Recover) {
            $psArgs += "-Recover"
        }

        & powershell @psArgs | Out-Null
        $exitCode = $LASTEXITCODE
        Add-CheckResult -Name "wsl_docker_health_script" -Ok ($exitCode -eq 0) -Detail "exit=$exitCode"
    }
    catch {
        Add-CheckResult -Name "wsl_docker_health_script" -Ok $false -Detail $_.Exception.Message
    }
}

if (-not $SkipApiChecks) {
    try {
        $healthUrl = $ApiBaseUrl.TrimEnd('/') + "/health"
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 8
        Add-CheckResult -Name "unified_api_health" -Ok ($resp.StatusCode -eq 200) -Detail "status=$($resp.StatusCode)"
    }
    catch {
        Add-CheckResult -Name "unified_api_health" -Ok $false -Detail $_.Exception.Message
    }

    $readonlyEndpoints = @(
        "/api/mothership/resources",
        "/api/file-secretary/inbox/status",
        "/api/pixel7/resources",
        "/api/x280/resources",
        "/api/devices/status"
    )

    foreach ($endpoint in $readonlyEndpoints) {
        $name = "readonly$endpoint"
        try {
            $url = $ApiBaseUrl.TrimEnd('/') + $endpoint
            $headers = @{ "X-API-Key" = $ReadonlyApiKey }
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -Headers $headers -TimeoutSec 10
            Add-CheckResult -Name $name -Ok ($resp.StatusCode -eq 200) -Detail "status=$($resp.StatusCode)"
        }
        catch {
            if ($StrictApi) {
                Add-CheckResult -Name $name -Ok $false -Detail $_.Exception.Message
            }
            else {
                Add-WarnResult -Name $name -Detail $_.Exception.Message
            }
        }
    }
}

if (-not $SkipCiChecks) {
    $workflows = @("Validate Ledger", "Workflow Policy Audit")

    foreach ($workflow in $workflows) {
        $key = "ci_" + ($workflow.ToLower().Replace(' ', '_'))
        $run = Get-LatestCompletedRun -WorkflowName $workflow

        if ($null -eq $run) {
            Add-CheckResult -Name $key -Ok $false -Detail "latest completed run not found"
            continue
        }

        $ok = ($run.conclusion -eq "success")
        $detail = "run=$($run.databaseId), conclusion=$($run.conclusion), title=$($run.displayTitle)"
        Add-CheckResult -Name $key -Ok $ok -Detail $detail
    }
}

$allOk = $true
foreach ($checkName in $results.checks.Keys) {
    if (-not $results.checks[$checkName].ok) {
        $allOk = $false
        break
    }
}

$results.notify = [ordered]@{
    webhook_enabled = (-not [string]::IsNullOrWhiteSpace($WebhookUrl))
    webhook_format = $WebhookFormat
    notify_on_success = [bool]$NotifyOnSuccess
}

$results.overall_ok = $allOk
$results | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8
$results | ConvertTo-Json -Depth 8 | Set-Content -Path $latestPath -Encoding UTF8

$shouldNotify = (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) -and ((-not $allOk) -or [bool]$NotifyOnSuccess)
if ($shouldNotify) {
    $failedChecks = @($results.checks.Keys | Where-Object { -not $results.checks[$_].ok })
    $warnChecks = @($results.checks.Keys | Where-Object {
        ($results.checks[$_].PSObject.Properties.Name -contains 'warning') -and [bool]$results.checks[$_].warning
    })

    $statusText = if ($allOk) { 'OK' } else { 'NG' }
    $messageLines = @(
        "ManaOS Daily Health Smoke: $statusText",
        "time: $($results.timestamp)",
        "distro: $Distro",
        "strict_api: $([bool]$StrictApi)",
        "recover: $([bool]$Recover)",
        "report: $reportPath"
    )
    if ($failedChecks.Count -gt 0) {
        $messageLines += ("failed: " + ($failedChecks -join ', '))
    }
    if ($warnChecks.Count -gt 0) {
        $messageLines += ("warnings: " + ($warnChecks -join ', '))
    }

    $webhookSent = Send-WebhookMessage -Url $WebhookUrl -Format $WebhookFormat -Message ($messageLines -join "`n") -Mention $WebhookMention
    $results.notify.sent = [bool]$webhookSent
    $results | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8
    $results | ConvertTo-Json -Depth 8 | Set-Content -Path $latestPath -Encoding UTF8
}

Write-Host ""
if ($allOk) {
    Write-Host "Daily health smoke: OK" -ForegroundColor Green
    Write-Host "Report: $reportPath" -ForegroundColor Green
    exit 0
}

Write-Host "Daily health smoke: NG" -ForegroundColor Red
Write-Host "Report: $reportPath" -ForegroundColor Yellow
exit 1
