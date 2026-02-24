param(
    [switch]$RemoteOnly,
    [switch]$Portrait,
    [switch]$Landscape,
    [int]$RetryDelaySeconds = 5,
    [int]$MaxDelaySeconds = 60,
    [int]$QuickFailSeconds = 10,
    [double]$BackoffFactor = 2.0,
    [int]$MaxRestarts = 0,
    [switch]$KillExisting,
    [switch]$TurnScreenOff
)

$ErrorActionPreference = 'Stop'

if ($RetryDelaySeconds -lt 1) { $RetryDelaySeconds = 1 }
if ($RetryDelaySeconds -gt 120) { $RetryDelaySeconds = 120 }
if ($MaxDelaySeconds -lt $RetryDelaySeconds) { $MaxDelaySeconds = $RetryDelaySeconds }
if ($MaxDelaySeconds -gt 600) { $MaxDelaySeconds = 600 }
if ($QuickFailSeconds -lt 1) { $QuickFailSeconds = 1 }
if ($QuickFailSeconds -gt 120) { $QuickFailSeconds = 120 }
if ($BackoffFactor -lt 1.2) { $BackoffFactor = 1.2 }
if ($BackoffFactor -gt 4.0) { $BackoffFactor = 4.0 }

$pidFile = Join-Path $PSScriptRoot '.pixel7_scrcpy_watch.pid'
$statusFile = Join-Path $PSScriptRoot '.pixel7_scrcpy_watch.status.json'
$logDir = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir ('pixel7_scrcpy_watch_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

function Write-Log([string]$msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $msg"
    $line | Out-Host
    Add-Content -Path $logFile -Value $line -ErrorAction SilentlyContinue
}

Set-Content -Path $pidFile -Value $PID -Encoding ASCII
Write-Log "=== Pixel7 scrcpy watch started (PID=$PID) ==="

$scrcpyAuto = Join-Path $PSScriptRoot 'pixel7_scrcpy_auto.ps1'
$recover = Join-Path $PSScriptRoot 'pixel7_adb_recover_wireless.ps1'

if (-not (Test-Path $scrcpyAuto)) {
    Write-Log "ERROR: not found: $scrcpyAuto"
    exit 2
}
if (-not (Test-Path $recover)) {
    Write-Log "ERROR: not found: $recover"
    exit 2
}

$restartCount = 0
$consecutiveQuickFails = 0
while ($true) {
    if ($MaxRestarts -gt 0 -and $restartCount -ge $MaxRestarts) {
        Write-Log "Reached MaxRestarts=$MaxRestarts. Stop."
        exit 0
    }

    try {
        if ($RemoteOnly) {
            & $recover -RemoteOnly | Out-Null
        } else {
            & $recover | Out-Null
        }
    } catch {
        Write-Log ("recover error: {0}" -f $_.Exception.Message)
    }

    $args = @()
    if ($RemoteOnly) { $args += '-RemoteOnly' }
    if ($Portrait) { $args += '-Portrait' }
    if ($Landscape) { $args += '-Landscape' }
    if ($KillExisting) { $args += '-KillExisting' }
    if ($TurnScreenOff) { $args += '-TurnScreenOff' }
    $args += '-Wait'

    Write-Log ("launch scrcpy_auto {0}" -f ($args -join ' '))

    $startedAt = Get-Date
    $exitCode = $null
    $exceptionText = $null
    try {
        & $scrcpyAuto @args
        $exitCode = $LASTEXITCODE
        Write-Log ("scrcpy_auto returned exit=$exitCode")
    } catch {
        $exceptionText = $_.Exception.Message
        Write-Log ("scrcpy_auto exception: {0}" -f $exceptionText)
    }

    $elapsed = (Get-Date) - $startedAt
    $elapsedSec = [int][math]::Round($elapsed.TotalSeconds)

    # すぐ落ちる(=QuickFail)が続く場合はバックオフ
    if ($elapsed.TotalSeconds -lt $QuickFailSeconds) {
        $consecutiveQuickFails += 1
    } else {
        $consecutiveQuickFails = 0
    }

    $delay = [double]$RetryDelaySeconds
    if ($consecutiveQuickFails -gt 0) {
        $exp = [math]::Min($consecutiveQuickFails, 8)
        $delay = $delay * [math]::Pow($BackoffFactor, $exp)
    }
    if ($delay -gt $MaxDelaySeconds) { $delay = $MaxDelaySeconds }
    if ($delay -lt $RetryDelaySeconds) { $delay = $RetryDelaySeconds }
    $delay = [int][math]::Round($delay)

    try {
        $status = [ordered]@{
            ts = (Get-Date).ToString('o')
            pid = $PID
            remoteOnly = [bool]$RemoteOnly
            portrait = [bool]$Portrait
            landscape = [bool]$Landscape
            turnScreenOff = [bool]$TurnScreenOff
            restarts = $restartCount
            quickFails = $consecutiveQuickFails
            elapsedSeconds = $elapsedSec
            exitCode = $exitCode
            exception = $exceptionText
            nextDelaySeconds = $delay
        }
        ($status | ConvertTo-Json -Depth 4) | Set-Content -Encoding UTF8 -Path $statusFile
    } catch {}

    $restartCount += 1
    Write-Log ("sleep {0}s then restart (count={1}, quickFails={2}, elapsed={3}s)" -f $delay, $restartCount, $consecutiveQuickFails, $elapsedSec)
    Start-Sleep -Seconds $delay
}
