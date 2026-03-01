param(
    [int]$FailThreshold = 3,
    [int]$TailLines = 200,
    [int]$CooldownMinutes = 30
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$outLog = Join-Path $logDir "file_secretary_fail_check.log"
$stateFile = Join-Path $logDir "file_secretary_fail_notify_state.json"
$notifyScript = Join-Path $repo "tools\notify_slack_webhook.ps1"
$ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$output = & powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\check_file_secretary_fail_streak.ps1" -TailLines $TailLines -FailThreshold $FailThreshold -Strict 2>&1
$exitCode = $LASTEXITCODE
$last = ($output | Select-Object -Last 1)

if (-not $last) {
    $last = "STATUS=UNKNOWN fail_streak=0 threshold=$FailThreshold reason=no_output"
}

$status = "UNKNOWN"
$failStreak = 0
if ($last -match "STATUS=([A-Z]+)") {
    $status = $Matches[1]
}
if ($last -match "fail_streak=(\d+)") {
    $failStreak = [int]$Matches[1]
}

$webhookUrl = $env:SLACK_WEBHOOK_URL
if ([string]::IsNullOrWhiteSpace($webhookUrl)) {
    $webhookUrl = [Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")
}

$now = Get-Date
$notify = "notify=none"
$inAlert = $false
$lastAlert = $null

if (Test-Path $stateFile) {
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        if ($null -ne $state.in_alert) {
            $inAlert = [bool]$state.in_alert
        }
        if ($state.last_alert) {
            $lastAlert = [DateTime]$state.last_alert
        }
    }
    catch {
    }
}

if (-not [string]::IsNullOrWhiteSpace($webhookUrl) -and (Test-Path $notifyScript)) {
    if ($status -eq "FAIL" -and $failStreak -ge $FailThreshold) {
        $cooldownOk = $true
        if ($lastAlert) {
            if ($now -lt $lastAlert.AddMinutes($CooldownMinutes)) {
                $cooldownOk = $false
            }
        }

        if ($cooldownOk) {
            $message = "🚨 File Secretary FAIL streak detected`nfail_streak=$failStreak threshold=$FailThreshold`n$last`nlog=$outLog"
            & powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WebhookUrl $webhookUrl -Text $message | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $notify = "notify=sent"
                @{
                    in_alert = $true
                    last_alert = $now.ToString("o")
                    last_recovery = $null
                } | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
            }
            else {
                $notify = "notify=error"
            }
        }
        else {
            $notify = "notify=suppressed_cooldown"
        }
    }
    elseif ($status -eq "OK" -and $inAlert) {
        $message = "✅ File Secretary recovered`n$last`nlog=$outLog"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $notifyScript -WebhookUrl $webhookUrl -Text $message | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $notify = "notify=recovered"
            @{
                in_alert = $false
                last_alert = if ($lastAlert) { $lastAlert.ToString("o") } else { $null }
                last_recovery = $now.ToString("o")
            } | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
        }
        else {
            $notify = "notify=error"
        }
    }
}
else {
    if ($status -eq "FAIL" -and $failStreak -ge $FailThreshold) {
        $notify = "notify=skipped_webhook_missing"
    }
}

Add-Content -Path $outLog -Value ("{0} exit={1} {2} {3}" -f $ts, $exitCode, $last, $notify)

exit $exitCode
