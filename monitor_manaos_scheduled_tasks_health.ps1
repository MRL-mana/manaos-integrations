param(
    [string[]]$TaskNames = @(
        'ManaOS_R12_Health_Watch_5min',
        'ManaOS_Pixel7_Holidays_Update_Annual',
        'ManaOS_Pixel7_Holidays_Update_Annual_Guard'
    ),
    [switch]$IgnoreMissing,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

function Get-TaskInfo {
    param([string]$TaskName)

    $output = schtasks /Query /TN $TaskName /V /FO CSV 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
        return [pscustomobject]@{
            task = $TaskName
            found = $false
            status = 'missing'
            last_result = $null
            last_run = $null
            next_run = $null
            ok = $false
            reason = 'task_not_found'
        }
    }

    $row = $output | ConvertFrom-Csv | Select-Object -First 1
    $lastResultRaw = [string]$row.'前回の結果'
    $lastRun = [string]$row.'前回の実行時刻'
    $nextRun = [string]$row.'次回の実行時刻'

    $lastResult = $null
    if (-not [string]::IsNullOrWhiteSpace($lastResultRaw)) {
        $trimmed = $lastResultRaw.Trim()
        if ($trimmed -match '^-?\d+$') {
            $lastResult = [int]$trimmed
        } else {
            $parsed = 0
            if ([int]::TryParse($trimmed, [ref]$parsed)) {
                $lastResult = $parsed
            }
        }
    }

    $isNeverRun = ($lastRun -eq '1999/11/30 0:00:00') -or ($lastRun -eq 'N/A')
    $ok = ($lastResult -eq 0) -or $isNeverRun

    return [pscustomobject]@{
        task = $TaskName
        found = $true
        status = [string]$row.'状態'
        last_result = $lastResult
        last_run = $lastRun
        next_run = $nextRun
        ok = $ok
        reason = if ($ok) { 'ok' } else { 'last_result_nonzero' }
    }
}

$results = @()
foreach ($name in $TaskNames) {
    $info = Get-TaskInfo -TaskName $name
    if (-not $info.found -and $IgnoreMissing.IsPresent) {
        $info.ok = $true
        $info.reason = 'ignored_missing'
    }
    $results += $info
}

$failed = @($results | Where-Object { -not $_.ok })

if ($Json.IsPresent) {
    [pscustomobject]@{
        ts = [DateTimeOffset]::Now.ToString('o')
        total = $results.Count
        failed = $failed.Count
        results = $results
    } | ConvertTo-Json -Depth 6
} else {
    Write-Host '=== ManaOS Scheduled Tasks Health ===' -ForegroundColor Cyan
    foreach ($entry in $results) {
        if ($entry.ok) {
            Write-Host "[OK] $($entry.task) status=$($entry.status) last_result=$($entry.last_result)" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] $($entry.task) reason=$($entry.reason) status=$($entry.status) last_result=$($entry.last_result)" -ForegroundColor Red
        }
    }
    Write-Host ("summary: {0} total / {1} failed" -f $results.Count, $failed.Count) -ForegroundColor Yellow
}

if ($failed.Count -gt 0) {
    exit 2
}

exit 0
