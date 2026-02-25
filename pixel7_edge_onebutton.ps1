param(
    [string]$PixelHost = "",
    [int]$ApiPort = 0,
    [string]$DeviceSerial = "",
    [switch]$AutoRecoverOnFailure,
    [int]$HealthTimeoutSec = 6,
    [int]$RecoveryWaitSec = 90,
    [int]$SmokeTimeoutSec = 8,
    [string]$WebhookUrl = "",
    [ValidateSet("generic", "slack", "discord")]
    [string]$WebhookFormat = "discord",
    [string]$WebhookMention = "",
    [switch]$NotifyOnSuccess
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$text) {
    Write-Host "`n== $text ==" -ForegroundColor Cyan
}

function Resolve-NotifySettings {
    param(
        [string]$InWebhookUrl,
        [string]$InWebhookFormat,
        [string]$InWebhookMention,
        [bool]$InNotifyOnSuccess
    )

    $resolvedUrl = $InWebhookUrl
    if ([string]::IsNullOrWhiteSpace($resolvedUrl) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_URL)) {
        $resolvedUrl = $env:MANAOS_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
        $resolvedUrl = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_URL', 'User')
    }

    $resolvedFormat = $InWebhookFormat
    if (-not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_FORMAT)) {
        $envFormat = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($envFormat -in @('generic', 'slack', 'discord')) {
            $resolvedFormat = $envFormat
        }
    }
    elseif (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_FORMAT', 'User'))) {
        $userFormat = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_FORMAT', 'User').Trim().ToLowerInvariant()
        if ($userFormat -in @('generic', 'slack', 'discord')) {
            $resolvedFormat = $userFormat
        }
    }

    $resolvedMention = $InWebhookMention
    if ([string]::IsNullOrWhiteSpace($resolvedMention) -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_WEBHOOK_MENTION)) {
        $resolvedMention = $env:MANAOS_WEBHOOK_MENTION
    }
    if ([string]::IsNullOrWhiteSpace($resolvedMention)) {
        $resolvedMention = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_MENTION', 'User')
    }

    $resolvedNotifyOnSuccess = $InNotifyOnSuccess
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace($env:MANAOS_NOTIFY_ON_SUCCESS)) {
        $notifyRaw = $env:MANAOS_NOTIFY_ON_SUCCESS.Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRaw -in @('1', 'true', 'yes', 'on'))
    }
    if (-not $resolvedNotifyOnSuccess -and -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('MANAOS_NOTIFY_ON_SUCCESS', 'User'))) {
        $notifyRawUser = [Environment]::GetEnvironmentVariable('MANAOS_NOTIFY_ON_SUCCESS', 'User').Trim().ToLowerInvariant()
        $resolvedNotifyOnSuccess = ($notifyRawUser -in @('1', 'true', 'yes', 'on'))
    }

    return [ordered]@{
        webhook_url = $resolvedUrl
        webhook_format = $resolvedFormat
        webhook_mention = $resolvedMention
        notify_on_success = [bool]$resolvedNotifyOnSuccess
    }
}

function Send-WebhookMessage {
    param(
        [string]$Url,
        [string]$Format,
        [string]$Mention,
        [string]$Text,
        [bool]$Success
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }

    $title = if ($Success) { 'Pixel7 edge check OK' } else { 'Pixel7 edge check FAIL' }
    $bodyText = if ([string]::IsNullOrWhiteSpace($Mention)) { $Text } else { "$Mention`n$Text" }

    try {
        switch ($Format) {
            'slack' {
                $payload = @{ text = "*$title*`n$bodyText" }
            }
            'discord' {
                $payload = @{ content = "**$title**`n$bodyText" }
            }
            default {
                $payload = @{ text = "$title`n$bodyText"; content = "$title`n$bodyText" }
            }
        }

        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 8 -Compress) -TimeoutSec 10 | Out-Null
    }
    catch {
        Write-Host ("[WARN] webhook notify failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

function Invoke-PwshFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    $output = @(& pwsh -NoProfile -ExecutionPolicy Bypass -File $FilePath @Arguments 2>&1)
    return [ordered]@{
        exit = $LASTEXITCODE
        output = $output
    }
}

function Test-PixelHealth {
    param(
        [string]$CtlScript,
        [string]$PixelHostValue,
        [int]$Port,
        [int]$TimeoutSec
    )

    try {
        $args = @(
            '-Action', 'Health',
            '-PixelHost', $PixelHostValue,
            '-Port', [string]$Port,
            '-TimeoutSec', [string]$TimeoutSec
        )
        $inv = Invoke-PwshFile -FilePath $CtlScript -Arguments $args
        if ($inv.exit -ne 0) {
            $detail = ($inv.output | Select-Object -Last 1)
            if ([string]::IsNullOrWhiteSpace([string]$detail)) {
                $detail = "pixel7_http_control exit=$($inv.exit)"
            }
            return [ordered]@{ ok = $false; detail = [string]$detail }
        }

        $obj = $null
        $raw = (($inv.output | ForEach-Object { [string]$_ }) -join "`n")
        $jsonPayload = ''
        $firstBrace = $raw.IndexOf('{')
        if ($firstBrace -ge 0) {
            $jsonPayload = $raw.Substring($firstBrace).Trim()
        }
        if ($raw -is [string]) {
            if (-not [string]::IsNullOrWhiteSpace($jsonPayload)) {
                try { $obj = $jsonPayload | ConvertFrom-Json } catch {}
            }
        }
        if ($null -eq $obj -and $null -ne $raw) {
            $obj = $raw
        }

        if ($obj -and $obj.status -eq 'healthy') {
            return [ordered]@{ ok = $true; detail = 'healthy' }
        }

        return [ordered]@{ ok = $false; detail = 'unexpected health payload' }
    }
    catch {
        return [ordered]@{ ok = $false; detail = $_.Exception.Message }
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logsDir = Join-Path $scriptRoot 'logs'
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

$healthCtl = Join-Path $scriptRoot 'pixel7_http_control.ps1'
$smokeScript = Join-Path $scriptRoot 'pixel7_http_smoketest.ps1'
$recoverAdbScript = Join-Path $scriptRoot 'pixel7_adb_recover_wireless.ps1'
$recoverGatewayScript = Join-Path $scriptRoot 'pixel7_termux_start_http_gateway.ps1'

if (-not (Test-Path $healthCtl)) { throw "Missing script: $healthCtl" }
if (-not (Test-Path $smokeScript)) { throw "Missing script: $smokeScript" }
if (-not (Test-Path $recoverAdbScript)) { throw "Missing script: $recoverAdbScript" }
if (-not (Test-Path $recoverGatewayScript)) { throw "Missing script: $recoverGatewayScript" }

if ([string]::IsNullOrWhiteSpace($PixelHost)) {
    if ($env:PIXEL7_API_HOST) { $PixelHost = $env:PIXEL7_API_HOST }
    elseif ($env:PIXEL7_TAILSCALE_IP) { $PixelHost = $env:PIXEL7_TAILSCALE_IP }
    elseif ($env:PIXEL7_IP) { $PixelHost = $env:PIXEL7_IP }
    else { $PixelHost = '100.84.2.125' }
}
if ($ApiPort -le 0) {
    if ($env:PIXEL7_API_PORT -and [int]::TryParse($env:PIXEL7_API_PORT, [ref]$ApiPort) -and $ApiPort -gt 0) {
    }
    else {
        $ApiPort = 5122
    }
}
if ([string]::IsNullOrWhiteSpace($DeviceSerial)) {
    $DeviceSerial = "$PixelHost:5555"
}

if ($HealthTimeoutSec -lt 3) { $HealthTimeoutSec = 3 }
if ($HealthTimeoutSec -gt 20) { $HealthTimeoutSec = 20 }
if ($RecoveryWaitSec -lt 30) { $RecoveryWaitSec = 30 }
if ($RecoveryWaitSec -gt 360) { $RecoveryWaitSec = 360 }
if ($SmokeTimeoutSec -lt 4) { $SmokeTimeoutSec = 4 }
if ($SmokeTimeoutSec -gt 30) { $SmokeTimeoutSec = 30 }

$notify = Resolve-NotifySettings -InWebhookUrl $WebhookUrl -InWebhookFormat $WebhookFormat -InWebhookMention $WebhookMention -InNotifyOnSuccess ([bool]$NotifyOnSuccess)
$WebhookUrl = [string]$notify.webhook_url
$WebhookFormat = [string]$notify.webhook_format
$WebhookMention = [string]$notify.webhook_mention
$NotifyOnSuccess = [bool]$notify.notify_on_success

Write-Host '=== Pixel7 Edge One-Button Check ===' -ForegroundColor Green
Write-Host ("host={0} port={1} serial={2}" -f $PixelHost, $ApiPort, $DeviceSerial) -ForegroundColor DarkGray

$status = [ordered]@{
    timestamp = (Get-Date).ToString('o')
    pixel_host = $PixelHost
    api_port = $ApiPort
    device_serial = $DeviceSerial
    auto_recover_on_failure = [bool]$AutoRecoverOnFailure
    health_before = $false
    recover_attempted = $false
    recover_adb_exit = $null
    recover_gateway_exit = $null
    health_after = $false
    smoke_exit = $null
    passed = $false
    detail = ''
}

Write-Step 'Health check (before)'
$pre = Test-PixelHealth -CtlScript $healthCtl -PixelHostValue $PixelHost -Port $ApiPort -TimeoutSec $HealthTimeoutSec
$status.health_before = [bool]$pre.ok
$status.detail = [string]$pre.detail
if ($pre.ok) {
    Write-Host '[OK] Pixel7 HTTP health is already healthy' -ForegroundColor Green
}
else {
    Write-Host ("[WARN] health before failed: {0}" -f $pre.detail) -ForegroundColor Yellow
}

if (-not $pre.ok -and $AutoRecoverOnFailure) {
    $status.recover_attempted = $true

    Write-Step 'Recover wireless ADB'
    $adbRec = Invoke-PwshFile -FilePath $recoverAdbScript -Arguments @('-PixelTailscaleIp', $PixelHost, '-RemoteOnly')
    $status.recover_adb_exit = $adbRec.exit
    if ($adbRec.output) { $adbRec.output | Out-Host }
    if ($status.recover_adb_exit -ne 0) {
        Write-Host ("[WARN] wireless ADB recover exit={0}" -f $status.recover_adb_exit) -ForegroundColor Yellow
    }

    Write-Step 'Start HTTP gateway via Termux (ADB assisted)'
    $gwRec = Invoke-PwshFile -FilePath $recoverGatewayScript -Arguments @(
        '-DeviceSerial', $DeviceSerial,
        '-WaitListenSec', [string]$RecoveryWaitSec,
        '-LogPath', '/storage/emulated/0/Download/pixel7_api_gateway_termux.log'
    )
    $status.recover_gateway_exit = $gwRec.exit
    if ($gwRec.output) { $gwRec.output | Out-Host }
    if ($status.recover_gateway_exit -ne 0) {
        Write-Host ("[WARN] gateway start exit={0}" -f $status.recover_gateway_exit) -ForegroundColor Yellow
    }

    Write-Step 'Health check (after recover)'
    $deadline = (Get-Date).AddSeconds($RecoveryWaitSec)
    $lastDetail = ''
    while ((Get-Date) -lt $deadline) {
        $post = Test-PixelHealth -CtlScript $healthCtl -PixelHostValue $PixelHost -Port $ApiPort -TimeoutSec $HealthTimeoutSec
        if ($post.ok) {
            $status.health_after = $true
            $lastDetail = 'healthy_after_recover'
            break
        }
        $lastDetail = [string]$post.detail
        Start-Sleep -Seconds 6
    }
    if (-not $status.health_after) {
        $status.detail = "recover_failed: $lastDetail"
        Write-Host ("[ERR] health did not recover: {0}" -f $lastDetail) -ForegroundColor Red
    }
}
else {
    $status.health_after = [bool]$status.health_before
}

if ($status.health_after) {
    Write-Step 'Run smoke test'
    $smoke = Invoke-PwshFile -FilePath $smokeScript -Arguments @('-TimeoutSec', [string]$SmokeTimeoutSec)
    $status.smoke_exit = $smoke.exit
    if ($smoke.output) { $smoke.output | Out-Host }
    if ($status.smoke_exit -eq 0) {
        Write-Host '[OK] smoke test passed' -ForegroundColor Green
    }
    else {
        Write-Host ("[WARN] smoke test exit={0}" -f $status.smoke_exit) -ForegroundColor Yellow
    }
}

$smokeExitResolved = 999
if ($null -ne $status.smoke_exit) {
    $smokeExitResolved = [int]$status.smoke_exit
}
$status.passed = ([bool]$status.health_after -and $smokeExitResolved -eq 0)
if ($status.passed) {
    $status.detail = 'healthy + smoketest passed'
}

$statePath = Join-Path $logsDir 'pixel7_edge_onebutton_latest.json'
$historyPath = Join-Path $logsDir 'pixel7_edge_onebutton_history.jsonl'

$status | ConvertTo-Json -Depth 8 | Set-Content -Path $statePath -Encoding UTF8
($status | ConvertTo-Json -Depth 8 -Compress) | Add-Content -Path $historyPath -Encoding UTF8

Write-Step 'Result'
Write-Host ("state : {0}" -f $statePath) -ForegroundColor White
Write-Host ("passed: {0}" -f $status.passed) -ForegroundColor $(if ($status.passed) { 'Green' } else { 'Red' })
Write-Host ("detail: {0}" -f $status.detail) -ForegroundColor Gray

if ($status.passed) {
    if ($NotifyOnSuccess) {
        Send-WebhookMessage -Url $WebhookUrl -Format $WebhookFormat -Mention $WebhookMention -Text ("Pixel7 edge check passed. host={0} port={1}" -f $PixelHost, $ApiPort) -Success $true
    }
    exit 0
}

Send-WebhookMessage -Url $WebhookUrl -Format $WebhookFormat -Mention $WebhookMention -Text ("Pixel7 edge check failed. detail={0} state={1}" -f $status.detail, $statePath) -Success $false
exit 2
