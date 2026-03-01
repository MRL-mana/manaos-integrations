param(
    [int]$WindowMinutes = 10,
    [int]$FailThreshold = 3,
    [switch]$NoPopup
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$logPath = Join-Path $repo "logs\dashboard_update.log"
$stateDir = Join-Path $repo "logs"
$stateFile = Join-Path $stateDir "dashboard_alert_state.json"
$auditLog = Join-Path $stateDir "dashboard_alert.log"

if ($WindowMinutes -lt 1) {
    throw "WindowMinutes must be >= 1"
}
if ($FailThreshold -lt 1) {
    throw "FailThreshold must be >= 1"
}

if (-not (Test-Path $logPath)) {
    exit 0
}

$since = (Get-Date).AddMinutes(-$WindowMinutes)
$lines = Get-Content $logPath -Tail 1000 |
    Where-Object { $_ -match "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} " }

$recent = New-Object System.Collections.Generic.List[string]

foreach ($line in $lines) {
    if ($line.Length -lt 19) {
        continue
    }

    $tsText = $line.Substring(0, 19)
    $parsed = [DateTime]::MinValue
    $ok = [DateTime]::TryParseExact(
        $tsText,
        "yyyy-MM-dd HH:mm:ss",
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$parsed
    )

    if ($ok -and $parsed -ge $since) {
        $recent.Add($line)
    }
}

$failCount = ($recent | Where-Object { $_ -match "\bFAIL\b" }).Count
$okCount = ($recent | Where-Object { $_ -match "\bOK\b" }).Count
$shouldAlert = ($failCount -ge $FailThreshold) -and ($okCount -eq 0)

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$now = Get-Date
$lastAlert = $null

if (Test-Path $stateFile) {
    try {
        $state = Get-Content $stateFile -Raw | ConvertFrom-Json
        if ($state.last_alert) {
            $lastAlert = [DateTime]$state.last_alert
        }
    }
    catch {
    }
}

if ($shouldAlert -and $lastAlert) {
    if ($now -lt $lastAlert.AddMinutes($WindowMinutes)) {
        Add-Content -Path $auditLog -Value (
            "{0} SKIP cooldown fail={1} ok={2}" -f
            $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount
        )
        exit 0
    }
}

if ($shouldAlert) {
    $title = "ManaOS Dashboard Update FAIL"
    $message = "Last ${WindowMinutes}m: FAIL=$failCount, OK=$okCount. Check logs/dashboard_update.log"

    if (-not $NoPopup) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($message, $title) | Out-Null
    }

    @{ last_alert = $now.ToString("o") } |
        ConvertTo-Json |
        Set-Content -Path $stateFile -Encoding UTF8

    Add-Content -Path $auditLog -Value (
        "{0} ALERT fail={1} ok={2}" -f
        $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount
    )
}
else {
    Add-Content -Path $auditLog -Value (
        "{0} OK fail={1} ok={2}" -f
        $now.ToString("yyyy-MM-dd HH:mm:ss"), $failCount, $okCount
    )
}

exit 0
