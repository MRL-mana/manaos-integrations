param(
    [int]$IntervalSeconds = 300,
    [int]$DegradedIntervalSeconds = 60,
    [int]$DegradedAfterFailures = 2,
    [int]$StrongRecoverAfterFailures = 5,
    [int]$StrongRecoverCooldownSec = 600,
    [switch]$EnableRebootTestRecovery,
    [int]$RebootTestAfterFailures = 8,
    [int]$RebootTestCooldownSec = 3600,
    [int]$FailureNotifyCooldownSec = 900,
    [int]$ForcedGatewayRecoverCooldownSec = 300,
    [switch]$AutoRecoverOnFailure,
    [switch]$RemoteOnly,
    [string]$PixelHost = "",
    [int]$ApiPort = 0,
    [string]$DeviceSerial = "",
    [switch]$NotifyOnRecover
)

$ErrorActionPreference = 'Stop'

if ($IntervalSeconds -lt 30) { $IntervalSeconds = 30 }
if ($IntervalSeconds -gt 3600) { $IntervalSeconds = 3600 }
if ($DegradedIntervalSeconds -lt 15) { $DegradedIntervalSeconds = 15 }
if ($DegradedIntervalSeconds -gt 1800) { $DegradedIntervalSeconds = 1800 }
if ($DegradedIntervalSeconds -gt $IntervalSeconds) { $DegradedIntervalSeconds = $IntervalSeconds }
if ($DegradedAfterFailures -lt 1) { $DegradedAfterFailures = 1 }
if ($DegradedAfterFailures -gt 20) { $DegradedAfterFailures = 20 }
if ($StrongRecoverAfterFailures -lt 1) { $StrongRecoverAfterFailures = 1 }
if ($StrongRecoverAfterFailures -gt 30) { $StrongRecoverAfterFailures = 30 }
if ($StrongRecoverAfterFailures -lt $DegradedAfterFailures) { $StrongRecoverAfterFailures = $DegradedAfterFailures }
if ($StrongRecoverCooldownSec -lt 60) { $StrongRecoverCooldownSec = 60 }
if ($StrongRecoverCooldownSec -gt 7200) { $StrongRecoverCooldownSec = 7200 }
if ($RebootTestAfterFailures -lt 1) { $RebootTestAfterFailures = 1 }
if ($RebootTestAfterFailures -gt 50) { $RebootTestAfterFailures = 50 }
if ($RebootTestAfterFailures -lt $StrongRecoverAfterFailures) { $RebootTestAfterFailures = $StrongRecoverAfterFailures }
if ($RebootTestCooldownSec -lt 300) { $RebootTestCooldownSec = 300 }
if ($RebootTestCooldownSec -gt 86400) { $RebootTestCooldownSec = 86400 }
if ($FailureNotifyCooldownSec -lt 60) { $FailureNotifyCooldownSec = 60 }
if ($FailureNotifyCooldownSec -gt 86400) { $FailureNotifyCooldownSec = 86400 }
if ($ForcedGatewayRecoverCooldownSec -lt 60) { $ForcedGatewayRecoverCooldownSec = 60 }
if ($ForcedGatewayRecoverCooldownSec -gt 3600) { $ForcedGatewayRecoverCooldownSec = 3600 }

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_edge_watch.pid'
$statusFile = Join-Path $root '.pixel7_edge_watch.status.json'
$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$logFile = Join-Path $logDir ('pixel7_edge_watch_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))
$onebutton = Join-Path $root 'pixel7_edge_onebutton.ps1'
$recoverAdbScript = Join-Path $root 'pixel7_adb_recover_wireless.ps1'
$recoverGatewayScript = Join-Path $root 'pixel7_termux_start_http_gateway.ps1'
$rebootTestScript = Join-Path $root 'pixel7_http_autostart_reboot_test.ps1'

if (-not (Test-Path $onebutton)) { throw "not found: $onebutton" }
if (-not (Test-Path $recoverAdbScript)) { throw "not found: $recoverAdbScript" }
if (-not (Test-Path $recoverGatewayScript)) { throw "not found: $recoverGatewayScript" }
if ($EnableRebootTestRecovery -and -not (Test-Path $rebootTestScript)) { throw "not found: $rebootTestScript" }

Set-Content -Encoding ASCII -NoNewline -Path $pidFile -Value $PID

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    $line | Out-Host
    Add-Content -Encoding UTF8 -Path $logFile -Value $line
}

function Resolve-NotifySettings {
    $url = ''
    $fmt = 'discord'
    $mention = ''

    if ($env:MANAOS_WEBHOOK_URL) { $url = $env:MANAOS_WEBHOOK_URL }
    if (-not $url) {
        $url = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_URL', 'User')
    }

    if ($env:MANAOS_WEBHOOK_FORMAT) {
        $f = $env:MANAOS_WEBHOOK_FORMAT.Trim().ToLowerInvariant()
        if ($f -in @('generic', 'slack', 'discord')) { $fmt = $f }
    } else {
        $f2 = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_FORMAT', 'User')
        if ($f2) {
            $f2 = $f2.Trim().ToLowerInvariant()
            if ($f2 -in @('generic', 'slack', 'discord')) { $fmt = $f2 }
        }
    }

    if ($env:MANAOS_WEBHOOK_MENTION) { $mention = $env:MANAOS_WEBHOOK_MENTION }
    if (-not $mention) {
        $mention = [Environment]::GetEnvironmentVariable('MANAOS_WEBHOOK_MENTION', 'User')
    }

    return [ordered]@{
        url = [string]$url
        format = [string]$fmt
        mention = [string]$mention
    }
}

function Send-WebhookMessage([string]$Url, [string]$Format, [string]$Mention, [string]$Title, [string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return }

    $bodyText = if ([string]::IsNullOrWhiteSpace($Mention)) { $Text } else { "$Mention`n$Text" }
    try {
        switch ($Format) {
            'slack' {
                $payload = @{ text = "*$Title*`n$bodyText" }
            }
            'discord' {
                $payload = @{ content = "**$Title**`n$bodyText" }
            }
            default {
                $payload = @{ text = "$Title`n$bodyText"; content = "$Title`n$bodyText" }
            }
        }
        Invoke-RestMethod -Uri $Url -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json -Depth 8 -Compress) -TimeoutSec 10 | Out-Null
    } catch {
        Write-Log ("[WARN] webhook notify failed: {0}" -f $_.Exception.Message)
    }
}

function Write-Status([hashtable]$obj) {
    $obj.ts = (Get-Date).ToString('o')
    $obj.pid = $PID
    $obj | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -Path $statusFile
}

$notify = Resolve-NotifySettings
$okCount = 0
$failCount = 0
$lastPassed = $null
$lastDetail = ''
$lastRunExit = 0
$currentIntervalSeconds = $IntervalSeconds
$lastFailureNotifyAt = $null
$lastForcedGatewayRecoverAt = $null
$lastStrongRecoverAt = $null
$lastRebootRecoveryAt = $null
$lastRecoveryAction = ''

Write-Log ("=== Pixel7 edge watch started (PID={0} interval={1}s degraded={2}s afterFails={3} strongAfter={4} rebootAfter={5} notifyCooldown={6}s forcedRecoverCooldown={7}s strongCooldown={8}s rebootCooldown={9}s rebootEnabled={10}) ===" -f $PID, $IntervalSeconds, $DegradedIntervalSeconds, $DegradedAfterFailures, $StrongRecoverAfterFailures, $RebootTestAfterFailures, $FailureNotifyCooldownSec, $ForcedGatewayRecoverCooldownSec, $StrongRecoverCooldownSec, $RebootTestCooldownSec, [bool]$EnableRebootTestRecovery)

Write-Status @{
    ok = $null
    okCount = $okCount
    failCount = $failCount
    intervalSeconds = $IntervalSeconds
    degradedIntervalSeconds = $DegradedIntervalSeconds
    degradedAfterFailures = $DegradedAfterFailures
    strongRecoverAfterFailures = $StrongRecoverAfterFailures
    strongRecoverCooldownSec = $StrongRecoverCooldownSec
    rebootTestRecoveryEnabled = [bool]$EnableRebootTestRecovery
    rebootTestAfterFailures = $RebootTestAfterFailures
    rebootTestCooldownSec = $RebootTestCooldownSec
    currentIntervalSeconds = $currentIntervalSeconds
    failureNotifyCooldownSec = $FailureNotifyCooldownSec
    forcedGatewayRecoverCooldownSec = $ForcedGatewayRecoverCooldownSec
    autoRecoverOnFailure = [bool]$AutoRecoverOnFailure
    remoteOnly = [bool]$RemoteOnly
    pixelHost = $PixelHost
    apiPort = $ApiPort
    deviceSerial = $DeviceSerial
    lastDetail = 'started'
    lastRunExit = $lastRunExit
    lastElapsedMs = 0
    lastRecoveryAction = $lastRecoveryAction
}

while ($true) {
    $start = Get-Date

    $args = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $onebutton
    )

    if ($AutoRecoverOnFailure) { $args += '-AutoRecoverOnFailure' }
    if ($PixelHost) { $args += @('-PixelHost', $PixelHost) }
    if ($ApiPort -gt 0) { $args += @('-ApiPort', [string]$ApiPort) }
    if ($DeviceSerial) { $args += @('-DeviceSerial', $DeviceSerial) }

    # 通知はwatch側で状態遷移時だけ送るため、onebutton側の通知は使わない
    $out = @(& pwsh @args 2>&1)
    $lastRunExit = $LASTEXITCODE

    $latestPath = Join-Path $logDir 'pixel7_edge_onebutton_latest.json'
    $passed = $false
    $detail = ''
    if (Test-Path $latestPath) {
        try {
            $st = Get-Content -Raw -Encoding UTF8 $latestPath | ConvertFrom-Json
            $passed = [bool]$st.passed
            $detail = [string]$st.detail
        } catch {
            $passed = ($lastRunExit -eq 0)
            $detail = 'status_parse_failed'
        }
    } else {
        $passed = ($lastRunExit -eq 0)
        $detail = 'status_file_missing'
    }

    $elapsedMs = [int]((Get-Date) - $start).TotalMilliseconds

    if ($passed) {
        $okCount++
        $failCount = 0
        Write-Log ("OK edge check (elapsed={0}ms)" -f $elapsedMs)

        if ($currentIntervalSeconds -ne $IntervalSeconds) {
            $currentIntervalSeconds = $IntervalSeconds
            Write-Log ("interval restored to normal: {0}s" -f $currentIntervalSeconds)
        }

        if ($lastPassed -eq $false -and $NotifyOnRecover) {
            Send-WebhookMessage -Url $notify.url -Format $notify.format -Mention $notify.mention -Title 'Pixel7 edge recovered' -Text ("Pixel7 edge check recovered. detail={0}" -f $detail)
        }

        $lastFailureNotifyAt = $null
    } else {
        $failCount++
        Write-Log ("NG edge check (fails={0} elapsed={1}ms detail={2})" -f $failCount, $elapsedMs, $detail)

        if ($failCount -ge $DegradedAfterFailures -and $currentIntervalSeconds -ne $DegradedIntervalSeconds) {
            $currentIntervalSeconds = $DegradedIntervalSeconds
            Write-Log ("interval switched to degraded: {0}s (fails={1})" -f $currentIntervalSeconds, $failCount)
        }

        if ($lastPassed -ne $false) {
            Send-WebhookMessage -Url $notify.url -Format $notify.format -Mention $notify.mention -Title 'Pixel7 edge failed' -Text ("Pixel7 edge became unhealthy. detail={0}" -f $detail)
            $lastFailureNotifyAt = Get-Date
        } elseif ($lastFailureNotifyAt) {
            $since = (Get-Date) - $lastFailureNotifyAt
            if ($since.TotalSeconds -ge $FailureNotifyCooldownSec) {
                Send-WebhookMessage -Url $notify.url -Format $notify.format -Mention $notify.mention -Title 'Pixel7 edge still failing' -Text ("Pixel7 remains unhealthy. fails={0} detail={1}" -f $failCount, $detail)
                $lastFailureNotifyAt = Get-Date
            }
        }

        $didStrongOrRebootRecovery = $false

        if ($AutoRecoverOnFailure -and $failCount -ge $StrongRecoverAfterFailures) {
            $doStrongRecover = $true
            if ($lastStrongRecoverAt) {
                $sinceStrong = (Get-Date) - $lastStrongRecoverAt
                if ($sinceStrong.TotalSeconds -lt $StrongRecoverCooldownSec) {
                    $doStrongRecover = $false
                }
            }

            if ($doStrongRecover) {
                try {
                    Write-Log ("strong recovery: wireless adb recover + gateway start (fails={0})" -f $failCount)
                    $recArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $recoverAdbScript, '-RestartAdb')
                    if ($RemoteOnly) { $recArgs += '-RemoteOnly' }
                    if ($PixelHost) { $recArgs += @('-PixelTailscaleIp', $PixelHost) }
                    $null = & pwsh @recArgs 2>&1

                    $effectiveSerial = $DeviceSerial
                    if ([string]::IsNullOrWhiteSpace($effectiveSerial) -and $PixelHost) {
                        $effectiveSerial = "$PixelHost:5555"
                    }
                    $gwArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $recoverGatewayScript, '-WaitListenSec', '120', '-LogPath', '/storage/emulated/0/Download/pixel7_api_gateway_termux.log')
                    if (-not [string]::IsNullOrWhiteSpace($effectiveSerial)) {
                        $gwArgs += @('-DeviceSerial', $effectiveSerial)
                    }
                    $null = & pwsh @gwArgs 2>&1

                    $lastStrongRecoverAt = Get-Date
                    $lastRecoveryAction = 'strong_recover'
                    $didStrongOrRebootRecovery = $true
                    Write-Log 'strong recovery: invoked'
                } catch {
                    Write-Log ("strong recovery failed: {0}" -f $_.Exception.Message)
                }
            }
        }

        if ($EnableRebootTestRecovery -and $AutoRecoverOnFailure -and $failCount -ge $RebootTestAfterFailures) {
            $doRebootRecovery = $true
            if ($lastRebootRecoveryAt) {
                $sinceReboot = (Get-Date) - $lastRebootRecoveryAt
                if ($sinceReboot.TotalSeconds -lt $RebootTestCooldownSec) {
                    $doRebootRecovery = $false
                }
            }

            if ($doRebootRecovery) {
                try {
                    Write-Log ("reboot-test recovery: invoking reboot test script (fails={0})" -f $failCount)
                    $rbArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $rebootTestScript, '-BootWaitSec', '35', '-HealthWaitSec', '360', '-SmokeTimeoutSec', '8')
                    if ($PixelHost) { $rbArgs += @('-TailscaleTarget', ("{0}:5555" -f $PixelHost)) }
                    if ($DeviceSerial) { $rbArgs += @('-DeviceSerial', $DeviceSerial) }

                    $null = & pwsh @rbArgs 2>&1
                    $rbExit = $LASTEXITCODE
                    $lastRebootRecoveryAt = Get-Date
                    $lastRecoveryAction = 'reboot_test'
                    $didStrongOrRebootRecovery = $true
                    Write-Log ("reboot-test recovery: done exit={0}" -f $rbExit)
                } catch {
                    Write-Log ("reboot-test recovery failed: {0}" -f $_.Exception.Message)
                }
            }
        }

        if (-not $didStrongOrRebootRecovery -and $AutoRecoverOnFailure -and $failCount -ge $DegradedAfterFailures) {
            $needForcedGatewayRecover = ($detail -in @('status_file_missing', 'status_parse_failed'))
            if ($needForcedGatewayRecover) {
                $doRecover = $true
                if ($lastForcedGatewayRecoverAt) {
                    $sinceRecover = (Get-Date) - $lastForcedGatewayRecoverAt
                    if ($sinceRecover.TotalSeconds -lt $ForcedGatewayRecoverCooldownSec) {
                        $doRecover = $false
                    }
                }

                if ($doRecover) {
                    try {
                        Write-Log 'forced recovery: start wireless adb recover + gateway start'
                        $recArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $recoverAdbScript, '-RestartAdb')
                        if ($RemoteOnly) { $recArgs += '-RemoteOnly' }
                        if ($PixelHost) { $recArgs += @('-PixelTailscaleIp', $PixelHost) }
                        $null = & pwsh @recArgs 2>&1

                        $effectiveSerial = $DeviceSerial
                        if ([string]::IsNullOrWhiteSpace($effectiveSerial)) {
                            if ($PixelHost) { $effectiveSerial = "$PixelHost:5555" }
                        }
                        $gwArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $recoverGatewayScript, '-WaitListenSec', '90', '-LogPath', '/storage/emulated/0/Download/pixel7_api_gateway_termux.log')
                        if (-not [string]::IsNullOrWhiteSpace($effectiveSerial)) {
                            $gwArgs += @('-DeviceSerial', $effectiveSerial)
                        }
                        $null = & pwsh @gwArgs 2>&1
                        $lastForcedGatewayRecoverAt = Get-Date
                        $lastRecoveryAction = 'forced_gateway_recover'
                        Write-Log 'forced recovery: gateway start invoked'
                    } catch {
                        Write-Log ("forced recovery failed: {0}" -f $_.Exception.Message)
                    }
                }
            }
        }
    }

    $lastPassed = $passed
    $lastDetail = $detail

    Write-Status @{
        ok = $passed
        okCount = $okCount
        failCount = $failCount
        intervalSeconds = $IntervalSeconds
        degradedIntervalSeconds = $DegradedIntervalSeconds
        degradedAfterFailures = $DegradedAfterFailures
        strongRecoverAfterFailures = $StrongRecoverAfterFailures
        strongRecoverCooldownSec = $StrongRecoverCooldownSec
        rebootTestRecoveryEnabled = [bool]$EnableRebootTestRecovery
        rebootTestAfterFailures = $RebootTestAfterFailures
        rebootTestCooldownSec = $RebootTestCooldownSec
        currentIntervalSeconds = $currentIntervalSeconds
        failureNotifyCooldownSec = $FailureNotifyCooldownSec
        forcedGatewayRecoverCooldownSec = $ForcedGatewayRecoverCooldownSec
        autoRecoverOnFailure = [bool]$AutoRecoverOnFailure
        remoteOnly = [bool]$RemoteOnly
        pixelHost = $PixelHost
        apiPort = $ApiPort
        deviceSerial = $DeviceSerial
        lastDetail = $lastDetail
        lastRunExit = $lastRunExit
        lastElapsedMs = $elapsedMs
        lastFailureNotifyAt = if ($lastFailureNotifyAt) { $lastFailureNotifyAt.ToString('o') } else { $null }
        lastForcedGatewayRecoverAt = if ($lastForcedGatewayRecoverAt) { $lastForcedGatewayRecoverAt.ToString('o') } else { $null }
        lastStrongRecoverAt = if ($lastStrongRecoverAt) { $lastStrongRecoverAt.ToString('o') } else { $null }
        lastRebootRecoveryAt = if ($lastRebootRecoveryAt) { $lastRebootRecoveryAt.ToString('o') } else { $null }
        lastRecoveryAction = $lastRecoveryAction
    }

    Start-Sleep -Seconds $currentIntervalSeconds
}
