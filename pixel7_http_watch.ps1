param(
    [int]$IntervalSeconds = 15,
    [int]$TimeoutSec = 3,
    [int]$FailThreshold = 3,
    [switch]$AttemptRecovery,
    [switch]$RemoteOnly
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$pidFile = Join-Path $root '.pixel7_http_watch.pid'
$statusFile = Join-Path $root '.pixel7_http_watch.status.json'
$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$logFile = Join-Path $logDir ('pixel7_http_watch_{0}.log' -f (Get-Date -Format 'yyyyMMdd'))

$httpCtl = Join-Path $root 'pixel7_http_control.ps1'
$adbCtl = Join-Path $root 'pixel7_remote_control.ps1'
$recoverCtl = Join-Path $root 'pixel7_adb_recover_wireless.ps1'
if (-not (Test-Path $httpCtl)) { throw "not found: $httpCtl" }
if (-not (Test-Path $adbCtl)) { throw "not found: $adbCtl" }
if (-not (Test-Path $recoverCtl)) { throw "not found: $recoverCtl" }

Set-Content -Encoding ASCII -NoNewline -Path $pidFile -Value $PID

function Write-Log([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -Encoding UTF8 -Path $logFile -Value $line
}

function Write-Status([hashtable]$obj) {
    $obj.ts = (Get-Date).ToString('o')
    $obj.pid = $PID
    $obj | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $statusFile
}

Write-Log "=== Pixel7 HTTP watch started (PID=$PID interval=${IntervalSeconds}s) ==="

$failCount = 0
$okCount = 0

while ($true) {
    $start = Get-Date
    $ok = $false
    $healthRaw = ''
    $err = ''

    try {
        $healthRaw = & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action Health -TimeoutSec $TimeoutSec 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0 -and $healthRaw -match 'healthy') { $ok = $true }
    } catch {
        $err = $_.Exception.Message
        $ok = $false
    }

    if ($ok) {
        $okCount++
        $failCount = 0
        Write-Log "OK health"
    } else {
        $failCount++
        Write-Log ("NG health (fails=$failCount) {0}" -f ($err))

        if ($AttemptRecovery -and $failCount -ge $FailThreshold) {
            Write-Log "AttemptRecovery: opening Termux via ADB"
            try {
                # Try to recover wireless ADB first (RemoteOnly => Tailscale only)
                $recArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $recoverCtl, '-RestartAdb')
                if ($RemoteOnly) { $recArgs += '-RemoteOnly' }
                & powershell @recArgs 2>&1 | Out-Null

                $pwshArgList = @('-NoProfile','-ExecutionPolicy','Bypass','-File', $adbCtl, '-Action','OpenTermux')
                & powershell @pwshArgList 2>&1 | Out-Null
            } catch {
                Write-Log ("Recovery failed: {0}" -f $_.Exception.Message)
            }
        }
    }

    $elapsedMs = [int]((Get-Date) - $start).TotalMilliseconds
    Write-Status @{
        ok = $ok
        okCount = $okCount
        failCount = $failCount
        intervalSeconds = $IntervalSeconds
        timeoutSec = $TimeoutSec
        failThreshold = $FailThreshold
        attemptRecovery = [bool]$AttemptRecovery
        remoteOnly = [bool]$RemoteOnly
        lastElapsedMs = $elapsedMs
        lastHealthRaw = ($healthRaw.Trim() | Select-Object -First 1)
    }

    Start-Sleep -Seconds $IntervalSeconds
}
