param(
    [int]$TailLines = 200,
    [int]$FailThreshold = 3,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$logPath = Join-Path $repo "logs\file_secretary_run.log"

if (-not (Test-Path $logPath)) {
    Write-Host "STATUS=UNKNOWN fail_streak=0 threshold=$FailThreshold reason=log_missing"
    exit 0
}

$lines = Get-Content $logPath -Tail $TailLines | Where-Object { $_ -match "STATUS=" }

$failStreak = 0
$lastStatus = "UNKNOWN"

for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    $line = $lines[$i]

    if ($line -match "STATUS=([A-Z]+)") {
        $status = $Matches[1]

        if ($lastStatus -eq "UNKNOWN") {
            $lastStatus = $status
        }

        if ($status -eq "FAIL") {
            $failStreak++
            continue
        }

        break
    }
}

Write-Host ("STATUS={0} fail_streak={1} threshold={2}" -f $lastStatus, $failStreak, $FailThreshold)

if ($Strict -and $failStreak -ge $FailThreshold) {
    exit 1
}

exit 0
