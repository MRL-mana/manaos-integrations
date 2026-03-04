$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot

function Get-PidInfo {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) {
        return [ordered]@{ running = $false; pid = $null; reason = 'no_pidfile' }
    }

    $pidText = (Get-Content -Raw -ErrorAction SilentlyContinue $PidFile).Trim()
    if (-not ($pidText -match '^\d+$')) {
        return [ordered]@{ running = $false; pid = $null; reason = 'invalid_pidfile' }
    }

    $pidValue = [int]$pidText
    $p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($p) {
        return [ordered]@{ running = $true; pid = $pidValue; reason = 'ok' }
    }

    return [ordered]@{ running = $false; pid = $pidValue; reason = 'pid_not_found' }
}

$components = [ordered]@{
    adb_keepalive = '.pixel7_adb_keepalive.pid'
    scrcpy_watch  = '.pixel7_scrcpy_watch.pid'
    reboot_watch  = '.pixel7_reboot_watch.pid'
    http_watch    = '.pixel7_http_watch.pid'
}

$result = [ordered]@{
    ts = (Get-Date).ToString('o')
    root = $root
    components = [ordered]@{}
}

foreach ($name in $components.Keys) {
    $pidFile = Join-Path $root $components[$name]
    $result.components[$name] = Get-PidInfo -PidFile $pidFile
}

$runningCount = @($result.components.GetEnumerator() | Where-Object { $_.Value.running }).Count
$result.summary = [ordered]@{
    total = $components.Count
    running = $runningCount
    all_running = ($runningCount -eq $components.Count)
}

$result | ConvertTo-Json -Depth 6
