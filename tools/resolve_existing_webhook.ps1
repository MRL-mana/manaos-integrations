param(
    [switch]$Apply,
    [switch]$NoTestPost
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

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

function Get-WebhookFormat {
    param([string]$Url)

    if ($Url -match "hooks\.slack\.com/services/") {
        return "slack"
    }
    if ($Url -match "discord\.com/api/webhooks/") {
        return "discord"
    }
    return "generic"
}

function Test-Webhook {
    param(
        [string]$Url,
        [string]$Format,
        [string]$Source,
        [bool]$NoPost
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return [pscustomobject]@{
            source = $Source
            format = $Format
            status = "empty"
            http = $null
            ok = $false
        }
    }

    if ($NoPost) {
        return [pscustomobject]@{
            source = $Source
            format = $Format
            status = "unchecked"
            http = $null
            ok = $false
        }
    }

    $payloadObj = switch ($Format) {
        "discord" { @{ content = "manaos webhook resolver test" } }
        default { @{ text = "manaos webhook resolver test" } }
    }

    try {
        $resp = Invoke-WebRequest -Uri $Url -Method Post -ContentType "application/json" -Body ($payloadObj | ConvertTo-Json -Depth 5) -UseBasicParsing
        $code = [int]$resp.StatusCode
        return [pscustomobject]@{
            source = $Source
            format = $Format
            status = if ($code -eq 200) { "ok" } else { "http_error" }
            http = $code
            ok = ($code -eq 200)
            url = $Url
        }
    }
    catch {
        $code = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        return [pscustomobject]@{
            source = $Source
            format = $Format
            status = if ($null -ne $code) { "http_error" } else { "network_or_unknown_error" }
            http = $code
            ok = $false
            url = $Url
        }
    }
}

$candidates = New-Object System.Collections.Generic.List[object]
$seen = New-Object 'System.Collections.Generic.HashSet[string]'

function Add-Candidate {
    param(
        [string]$Source,
        [string]$Url,
        [string]$Format
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }

    if ($seen.Add($Url)) {
        $candidates.Add([pscustomobject]@{
            source = $Source
            url = $Url
            format = if ([string]::IsNullOrWhiteSpace($Format)) { Get-WebhookFormat -Url $Url } else { $Format }
        })
    }
}

Add-Candidate -Source "session:MANAOS_WEBHOOK_URL" -Url $env:MANAOS_WEBHOOK_URL -Format $env:MANAOS_WEBHOOK_FORMAT
Add-Candidate -Source "user:MANAOS_WEBHOOK_URL" -Url ([Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_URL", "User")) -Format ([Environment]::GetEnvironmentVariable("MANAOS_WEBHOOK_FORMAT", "User"))
Add-Candidate -Source "session:SLACK_WEBHOOK_URL" -Url $env:SLACK_WEBHOOK_URL -Format "slack"
Add-Candidate -Source "user:SLACK_WEBHOOK_URL" -Url ([Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")) -Format "slack"

$dotenvPath = Join-Path $repo ".env"
Add-Candidate -Source "dotenv:MANAOS_WEBHOOK_URL" -Url (Get-DotEnvValue -Path $dotenvPath -Key "MANAOS_WEBHOOK_URL") -Format (Get-DotEnvValue -Path $dotenvPath -Key "MANAOS_WEBHOOK_FORMAT")
Add-Candidate -Source "dotenv:SLACK_WEBHOOK_URL" -Url (Get-DotEnvValue -Path $dotenvPath -Key "SLACK_WEBHOOK_URL") -Format "slack"

$statePath = Join-Path $repo "notification_system_state.json"
if (Test-Path $statePath) {
    try {
        $state = Get-Content -Path $statePath -Raw | ConvertFrom-Json
        Add-Candidate -Source "notification_system_state:slack_webhook_url" -Url ([string]$state.slack_webhook_url) -Format "slack"
        Add-Candidate -Source "notification_system_state:discord_webhook_url" -Url ([string]$state.discord_webhook_url) -Format "discord"
    }
    catch {
    }
}

$enhancedPath = Join-Path $repo "notification_hub_enhanced_config.json"
if (Test-Path $enhancedPath) {
    try {
        $cfg = Get-Content -Path $enhancedPath -Raw | ConvertFrom-Json
        Add-Candidate -Source "notification_hub_enhanced:slack_webhook_url" -Url ([string]$cfg.slack_webhook_url) -Format "slack"
    }
    catch {
    }
}

if ($candidates.Count -eq 0) {
    Write-Host "NO_CANDIDATE_FOUND"
    exit 1
}

$results = New-Object System.Collections.Generic.List[object]
foreach ($candidate in $candidates) {
    $result = Test-Webhook -Url $candidate.url -Format $candidate.format -Source $candidate.source -NoPost:$NoTestPost
    if (-not $result.PSObject.Properties.Match('url').Count) {
        $result | Add-Member -NotePropertyName url -NotePropertyValue $candidate.url
    }
    $results.Add($result)
}

$results | ForEach-Object {
    $httpText = if ($_.http -ne $null) { $_.http } else { "-" }
    Write-Host ("source={0} format={1} status={2} http={3}" -f $_.source, $_.format, $_.status, $httpText)
}

$winner = $results | Where-Object { $_.ok } | Select-Object -First 1

if (-not $winner) {
    Write-Host "NO_VALID_WEBHOOK"
    exit 1
}

Write-Host ("WINNER source={0} format={1}" -f $winner.source, $winner.format)

if ($Apply) {
    $setScript = Join-Path $repo "set_openwebui_notify_env.ps1"
    if (-not (Test-Path $setScript)) {
        throw "set script missing: $setScript"
    }

    & powershell -NoProfile -ExecutionPolicy Bypass -File $setScript -WebhookUrl $winner.url -WebhookFormat $winner.format | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "set_openwebui_notify_env.ps1 failed with exit=$LASTEXITCODE"
    }

    Write-Host "APPLIED_TO_MANAOS_WEBHOOK_ENV"
}

exit 0
