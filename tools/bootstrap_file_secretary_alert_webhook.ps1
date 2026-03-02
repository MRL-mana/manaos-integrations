param(
    [Parameter(Mandatory = $true)]
    [string]$WebhookUrl,
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "slack",
    [string]$WebhookMention = "",
    [int]$FailThreshold = 3,
    [int]$CooldownMinutes = 30
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$runLog = Join-Path $repo "logs\file_secretary_run.log"
$failLog = Join-Path $repo "logs\file_secretary_fail_check.log"
$stateFile = Join-Path $repo "logs\file_secretary_fail_notify_state.json"
$setNotifyScript = Join-Path $repo "set_openwebui_notify_env.ps1"
$runCheckScript = Join-Path $repo "tools\run_file_secretary_fail_check.ps1"

if (-not (Test-Path $setNotifyScript)) {
    throw "script missing: $setNotifyScript"
}
if (-not (Test-Path $runCheckScript)) {
    throw "script missing: $runCheckScript"
}

# 1) Validate webhook before saving
$validateText = "ManaOS file-secretary webhook validation"
$payload = switch ($WebhookFormat) {
    "discord" { @{ content = if ([string]::IsNullOrWhiteSpace($WebhookMention)) { $validateText } else { "$WebhookMention`n$validateText" } } }
    default { @{ text = if ([string]::IsNullOrWhiteSpace($WebhookMention)) { $validateText } else { "$WebhookMention`n$validateText" } } }
}

try {
    $resp = Invoke-WebRequest -Uri $WebhookUrl -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 5) -UseBasicParsing
    if ([int]$resp.StatusCode -ne 200) {
        throw "webhook validate failed: http=$([int]$resp.StatusCode)"
    }
}
catch {
    $code = $null
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
        $code = [int]$_.Exception.Response.StatusCode
    }
    if ($code -ne $null) {
        throw "webhook validate failed: http=$code"
    }
    throw "webhook validate failed: $($_.Exception.Message)"
}

# 2) Save notify env by existing script
& powershell -NoProfile -ExecutionPolicy Bypass -File $setNotifyScript -WebhookUrl $WebhookUrl -WebhookFormat $WebhookFormat -WebhookMention $WebhookMention | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "set_openwebui_notify_env.ps1 failed with exit=$LASTEXITCODE"
}

# 3) Reset state for one-shot test
Remove-Item $stateFile -ErrorAction SilentlyContinue

# 4) Inject FAIL streak and run checker
$ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
1..3 | ForEach-Object {
    Add-Content $runLog -Value "$ts STATUS=FAIL processed=0 errors=1 skipped=0 duration_ms=1"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $runCheckScript -FailThreshold $FailThreshold -CooldownMinutes $CooldownMinutes | Out-Null

# 5) Inject OK and run checker
$ts2 = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
Add-Content $runLog -Value "$ts2 STATUS=OK processed=0 errors=0 skipped=0 duration_ms=1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $runCheckScript -FailThreshold $FailThreshold -CooldownMinutes $CooldownMinutes | Out-Null

# 6) Assert last records include sent + recovered
$tail = Get-Content $failLog -Tail 20
$hasSent = [bool]($tail | Where-Object { $_ -match "notify=sent|notify=sent_fallback" })
$hasRecovered = [bool]($tail | Where-Object { $_ -match "notify=recovered_sent|notify=recovered_sent_fallback" })

if ($hasSent -and $hasRecovered) {
    Write-Host "PASS: alert and recovery notifications were emitted." -ForegroundColor Green
    exit 0
}

Write-Host "FAIL: expected notification markers not found in fail-check log." -ForegroundColor Red
$tail | Select-Object -Last 8
exit 1
