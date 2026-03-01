param(
    [int]$WindowMinutes = 10,
    [int]$FailThreshold = 3,
    [switch]$NoPopup,
    [ValidateRange(1, 10)]
    [int]$NotifyRetryCount = 3,
    [ValidateRange(0, 60)]
    [int]$NotifyRetryInitialDelaySec = 1,
    [ValidateRange(1.0, 5.0)]
    [double]$NotifyRetryBackoffFactor = 2.0
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$logPath = Join-Path $repo "logs\dashboard_update.log"
$stateDir = Join-Path $repo "logs"
$stateFile = Join-Path $stateDir "dashboard_alert_state.json"
$auditLog = Join-Path $stateDir "dashboard_alert.log"
$notifyScript = Join-Path $repo "tools\notify_slack_webhook.ps1"
$dotenvPath = Join-Path $repo ".env"

function Get-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        return ""
    }

    $line = Get-Content -Path $Path | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $line) {
        return ""
    }

    $value = ($line -replace "^\s*$Key\s*=\s*", "").Trim()
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    return $value
}

function Resolve-WebhookSettings {
    $sessionManaosWebhook = $env:MANAOS_WEBHOOK_URL
    $userManaosWebhook = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")
    $sessionSlackWebhook = $env:SLACK_WEBHOOK_URL
    $userSlackWebhook = [Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")

    $webhookUrl = ""
    $webhookSource = "none"

    if (-not [string]::IsNullOrWhiteSpace($sessionManaosWebhook)) {
        $webhookUrl = $sessionManaosWebhook
        $webhookSource = "manaos_session"
    }
    elseif (-not [string]::IsNullOrWhiteSpace($userManaosWebhook)) {
        $webhookUrl = $userManaosWebhook
        $webhookSource = "manaos_user"
    }
    elseif (-not [string]::IsNullOrWhiteSpace($sessionSlackWebhook)) {
        $webhookUrl = $sessionSlackWebhook
        $webhookSource = "slack_session"
    }
    elseif (-not [string]::IsNullOrWhiteSpace($userSlackWebhook)) {
        $webhookUrl = $userSlackWebhook
        $webhookSource = "slack_user"
    }
    else {
        $dotManaosWebhook = Get-DotEnvValue -Path $dotenvPath -Key "MANAOS_WEBHOOK_URL"
        $dotSlackWebhook = Get-DotEnvValue -Path $dotenvPath -Key "SLACK_WEBHOOK_URL"
        if (-not [string]::IsNullOrWhiteSpace($dotManaosWebhook)) {
            $webhookUrl = $dotManaosWebhook
            $webhookSource = "dotenv_manaos"
        }
        elseif (-not [string]::IsNullOrWhiteSpace($dotSlackWebhook)) {
            $webhookUrl = $dotSlackWebhook
            $webhookSource = "dotenv_slack"
        }
    }

    $webhookFormat = "slack"
    $sessionFormat = $env:MANAOS_WEBHOOK_FORMAT
    $userFormat = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User")
    if (-not [string]::IsNullOrWhiteSpace($sessionFormat)) {
        $fmt = $sessionFormat.Trim().ToLowerInvariant()
        if ($fmt -in @("generic", "slack", "discord")) {
            $webhookFormat = $fmt
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace($userFormat)) {
        $fmt = $userFormat.Trim().ToLowerInvariant()
        if ($fmt -in @("generic", "slack", "discord")) {
            $webhookFormat = $fmt
        }
    }
    elseif ($webhookSource -eq "dotenv_manaos") {
        $fmt = (Get-DotEnvValue -Path $dotenvPath -Key "MANAOS_WEBHOOK_FORMAT").Trim().ToLowerInvariant()
        if ($fmt -in @("generic", "slack", "discord")) {
            $webhookFormat = $fmt
        }
    }

    $webhookMention = ""
    $sessionMention = $env:MANAOS_WEBHOOK_MENTION
    $userMention = [Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_MENTION", "User")
    if (-not [string]::IsNullOrWhiteSpace($sessionMention)) {
        $webhookMention = $sessionMention
    }
    elseif (-not [string]::IsNullOrWhiteSpace($userMention)) {
        $webhookMention = $userMention
    }
    elseif ($webhookSource -eq "dotenv_manaos") {
        $webhookMention = Get-DotEnvValue -Path $dotenvPath -Key "MANAOS_WEBHOOK_MENTION"
    }

    return [pscustomobject]@{
        url = $webhookUrl
        source = $webhookSource
        format = $webhookFormat
        mention = $webhookMention
    }
}

function Send-AlertWebhook {
    param(
        [string]$Title,
        [string]$Body,
        [int]$RetryCount,
        [int]$InitialDelaySec,
        [double]$BackoffFactor
    )

    if (-not (Test-Path $notifyScript)) {
        return "notify=skipped_notify_script_missing"
    }

    $settings = Resolve-WebhookSettings
    if ([string]::IsNullOrWhiteSpace($settings.url)) {
        return "notify=skipped_webhook_missing"
    }

    $text = "$Title`n$Body"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WebhookUrl $settings.url -Text $text -Format $settings.format -Mention $settings.mention -RetryCount $RetryCount -InitialDelaySec $InitialDelaySec -BackoffFactor $BackoffFactor | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return "notify=sent source=$($settings.source) format=$($settings.format)"
    }

    return "notify=error source=$($settings.source) format=$($settings.format)"
}

if ($WindowMinutes -lt 1) {
    throw "WindowMinutes must be >= 1"
}
if ($FailThreshold -lt 1) {
    throw "FailThreshold must be >= 1"
}

if (-not (Test-Path $logPath)) {
    exit 0
}

$since = (Get-Date).AddMinutes(-$WindowMinutes)
$lines = Get-Content $logPath -Tail 1000 |
    Where-Object { $_ -match "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} " }

$recent = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    if ($line.Length -lt 19) {
        continue
    }

    $tsText = $line.Substring(0, 19)
    $parsed = [DateTime]::MinValue
    $ok = [DateTime]::TryParseExact(
        $tsText,
        "yyyy-MM-dd HH:mm:ss",
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$parsed
    )

    if ($ok -and $parsed -ge $since) {
        $recent.Add($line)
    }
}

$failCount = ($recent | Where-Object { $_ -match "\bFAIL\b" }).Count
$okCount = ($recent | Where-Object { $_ -match "\bOK\b" }).Count
$shouldAlert = ($failCount -ge $FailThreshold) -and ($okCount -eq 0)

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$now = Get-Date
$lastAlert = $null
$lastRecovery = $null
$inAlert = $false

if (Test-Path $stateFile) {
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        if ($state.last_alert) {
            $lastAlert = [DateTime]$state.last_alert
        }
        if ($state.last_recovery) {
            $lastRecovery = [DateTime]$state.last_recovery
        }
        if ($null -ne $state.in_alert) {
            $inAlert = [bool]$state.in_alert
        }
    }
    catch {
    }
}

if ($shouldAlert -and $lastAlert) {
    if ($now -lt $lastAlert.AddMinutes($WindowMinutes)) {
        Add-Content -Path $auditLog -Value (
            "{0} SKIP cooldown fail={1} ok={2}" -f
            $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount
        )
        exit 0
    }
}

if ($shouldAlert) {
    $title = "ManaOS Dashboard Update FAIL"
    $message = "Last ${WindowMinutes}m: FAIL=$failCount, OK=$okCount. Check logs/dashboard_update.log"
    $notifyResult = Send-AlertWebhook -Title $title -Body $message -RetryCount $NotifyRetryCount -InitialDelaySec $NotifyRetryInitialDelaySec -BackoffFactor $NotifyRetryBackoffFactor

    if (-not $NoPopup) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($message, $title) | Out-Null
    }

    @{
        last_alert = $now.ToString("o")
        last_recovery = if ($lastRecovery) { $lastRecovery.ToString("o") } else { $null }
        in_alert = $true
    } |
        ConvertTo-Json |
        Set-Content -Path $stateFile -Encoding UTF8

    Add-Content -Path $auditLog -Value (
        "{0} ALERT fail={1} ok={2} {3}" -f
        $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount, $notifyResult
    )
}
else {
    if ($inAlert -and $okCount -gt 0) {
        $title = "ManaOS Dashboard Update RECOVERED"
        $message = "Recovered: Last ${WindowMinutes}m now includes OK entries (FAIL=$failCount, OK=$okCount)."
        $notifyResult = Send-AlertWebhook -Title $title -Body $message -RetryCount $NotifyRetryCount -InitialDelaySec $NotifyRetryInitialDelaySec -BackoffFactor $NotifyRetryBackoffFactor

        if (-not $NoPopup) {
            Add-Type -AssemblyName PresentationFramework
            [System.Windows.MessageBox]::Show($message, $title) | Out-Null
        }

        @{
            last_alert = if ($lastAlert) { $lastAlert.ToString("o") } else { $null }
            last_recovery = $now.ToString("o")
            in_alert = $false
        } |
            ConvertTo-Json |
            Set-Content -Path $stateFile -Encoding UTF8

        Add-Content -Path $auditLog -Value (
            "{0} RECOVERED fail={1} ok={2} {3}" -f
            $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount, $notifyResult
        )
        exit 0
    }

    Add-Content -Path $auditLog -Value (
        "{0} OK fail={1} ok={2}" -f
        $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount
    )
}

exit 0
