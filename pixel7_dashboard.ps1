param(
    [switch]$OpenLogsFolder
)

$ErrorActionPreference = 'Stop'

function Get-JsonOrNull([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    try {
        return (Get-Content -Raw -Encoding UTF8 $path | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-LatestFileOrNull([string]$dir, [string]$filter) {
    try {
        return (Get-ChildItem -Path $dir -Filter $filter -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
    } catch {
        return $null
    }
}

$root = $PSScriptRoot
$logsDir = Join-Path $root 'logs'

Write-Host '=== Pixel7 Dashboard ===' -ForegroundColor Cyan
Write-Host ("root: {0}" -f $root) -ForegroundColor DarkGray

# HTTP gateway (optional)
$httpCtl = Join-Path $root 'pixel7_http_control.ps1'
$tokenFile = Join-Path $root '.pixel7_api_token.txt'
Write-Host "\n[http gateway]" -ForegroundColor Gray
if (-not (Test-Path $httpCtl)) {
    Write-Host 'pixel7_http_control.ps1: (not found)' -ForegroundColor DarkGray
} elseif (-not $env:PIXEL7_API_TOKEN -and -not (Test-Path $tokenFile)) {
    Write-Host 'PIXEL7_API_TOKEN: (not set)' -ForegroundColor DarkGray
    Write-Host ("hint: set env PIXEL7_API_TOKEN or create {0}" -f $tokenFile) -ForegroundColor DarkGray
} else {
    try {
        $health = & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action Health -TimeoutSec 3 2>$null
        Write-Host ('health: {0}' -f ($health | Out-String).Trim()) -ForegroundColor White
    } catch {
        Write-Host ('health: (down) {0}' -f $_.Exception.Message) -ForegroundColor Yellow
    }

    try {
        $st = & powershell -NoProfile -ExecutionPolicy Bypass -File $httpCtl -Action Status -TimeoutSec 5 2>$null
        if ($st) {
            $o = ($st | Out-String) | ConvertFrom-Json
            if ($o.resources -and $o.resources.battery) {
                Write-Host ("battery(level={0} status={1})" -f $o.resources.battery.level, $o.resources.battery.status) -ForegroundColor White
            }
            if ($o.resources -and $o.resources.memory) {
                Write-Host ("memory(usage={0}% availMB={1})" -f $o.resources.memory.usage_percent, $o.resources.memory.available_mb) -ForegroundColor White
            }
        }
    } catch {
        Write-Host ('status: (unavailable) {0}' -f $_.Exception.Message) -ForegroundColor DarkGray
    }
}

# http watch status
$httpWatchStatus = Join-Path $root '.pixel7_http_watch.status.json'
$httpWatchPid = Join-Path $root '.pixel7_http_watch.pid'
Write-Host "\n[http watch]" -ForegroundColor Gray
if (Test-Path $httpWatchPid) {
    $watchProcessId = (Get-Content -Raw -ErrorAction SilentlyContinue $httpWatchPid).Trim()
    Write-Host ("pidfile: {0}" -f $watchProcessId) -ForegroundColor DarkGray
}
$hw = Get-JsonOrNull $httpWatchStatus
if ($hw) {
    Write-Host ("ok={0} failCount={1} okCount={2} interval={3}s recovery={4}" -f $hw.ok,$hw.failCount,$hw.okCount,$hw.intervalSeconds,$hw.attemptRecovery) -ForegroundColor White
    Write-Host ("ts={0}" -f $hw.ts) -ForegroundColor DarkGray
} else {
    Write-Host 'status: (none)' -ForegroundColor DarkGray
}

# ADB devices
$scrcpyDir = Join-Path $env:USERPROFILE 'Desktop\scrcpy\scrcpy-win64-v3.3.4'
$adbExe = Join-Path $scrcpyDir 'adb.exe'
if (Test-Path $adbExe) {
    Write-Host "\n[adb devices]" -ForegroundColor Gray
    try {
        (& $adbExe devices 2>&1 | Out-String).TrimEnd() | Out-Host
    } catch {
        Write-Host ("adb devices failed: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
} else {
    Write-Host "adb.exe not found" -ForegroundColor Yellow
}

# scrcpy watch status
$scrcpyWatchStatus = Join-Path $root '.pixel7_scrcpy_watch.status.json'
$scrcpyWatchPid = Join-Path $root '.pixel7_scrcpy_watch.pid'
Write-Host "\n[scrcpy watch]" -ForegroundColor Gray
if (Test-Path $scrcpyWatchPid) {
    $watchProcessId = (Get-Content -Raw -ErrorAction SilentlyContinue $scrcpyWatchPid).Trim()
    Write-Host ("pidfile: {0}" -f $watchProcessId) -ForegroundColor DarkGray
}
$sw = Get-JsonOrNull $scrcpyWatchStatus
if ($sw) {
    Write-Host ("remoteOnly={0} turnScreenOff={1} restarts={2} quickFails={3} nextDelay={4}s exit={5} elapsed={6}s" -f $sw.remoteOnly,$sw.turnScreenOff,$sw.restarts,$sw.quickFails,$sw.nextDelaySeconds,$sw.exitCode,$sw.elapsedSeconds) -ForegroundColor White
    Write-Host ("ts={0}" -f $sw.ts) -ForegroundColor DarkGray
} else {
    Write-Host 'status: (none)' -ForegroundColor DarkGray
}

# reboot watch status
$rebootWatchStatus = Join-Path $root '.pixel7_reboot_watch.status.json'
$rebootWatchPid = Join-Path $root '.pixel7_reboot_watch.pid'
Write-Host "\n[reboot watch]" -ForegroundColor Gray
if (Test-Path $rebootWatchPid) {
    $watchProcessId = (Get-Content -Raw -ErrorAction SilentlyContinue $rebootWatchPid).Trim()
    Write-Host ("pidfile: {0}" -f $watchProcessId) -ForegroundColor DarkGray
}
$rw = Get-JsonOrNull $rebootWatchStatus
if ($rw) {
    Write-Host ("remoteOnly={0} serial={1} bootCompleted={2} bootId={3}" -f $rw.remoteOnly,$rw.serial,$rw.bootCompleted,$rw.bootId) -ForegroundColor White
    if ($rw.pendingBootId) {
        Write-Host ("pendingBootId={0}" -f $rw.pendingBootId) -ForegroundColor Yellow
    }
    Write-Host ("ts={0}" -f $rw.ts) -ForegroundColor DarkGray
} else {
    Write-Host 'status: (none)' -ForegroundColor DarkGray
}

# latest scrcpy logs
Write-Host "\n[latest scrcpy stderr]" -ForegroundColor Gray
$latestErr = Get-LatestFileOrNull $logsDir 'scrcpy_auto_*.err.log'
if ($latestErr) {
    Write-Host ("file: {0}" -f $latestErr.FullName) -ForegroundColor DarkGray
    try { Get-Content $latestErr.FullName -Tail 30 -ErrorAction SilentlyContinue | Out-Host } catch {}
} else {
    Write-Host '(none)' -ForegroundColor DarkGray
}

# latest reboot bundles
Write-Host "\n[reboot bundles]" -ForegroundColor Gray
$rebootDir = Join-Path $logsDir 'pixel7_reboots'
if (Test-Path $rebootDir) {
    $bundles = Get-ChildItem -Path $rebootDir -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5
    if ($bundles) {
        $bundles | Select-Object Name,LastWriteTime | Format-Table -AutoSize | Out-Host
    } else {
        Write-Host '(none)' -ForegroundColor DarkGray
    }
} else {
    Write-Host '(no pixel7_reboots dir yet)' -ForegroundColor DarkGray
}

if ($OpenLogsFolder -and (Test-Path $logsDir)) {
    Start-Process $logsDir | Out-Null
}

Write-Host "\nOK" -ForegroundColor Green
