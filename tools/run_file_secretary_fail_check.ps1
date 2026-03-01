param(
    [int]$FailThreshold = 3,
    [int]$TailLines = 200
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repo

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$outLog = Join-Path $logDir "file_secretary_fail_check.log"
$ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$output = & powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\check_file_secretary_fail_streak.ps1" -TailLines $TailLines -FailThreshold $FailThreshold -Strict 2>&1
$exitCode = $LASTEXITCODE
$last = ($output | Select-Object -Last 1)

if (-not $last) {
    $last = "STATUS=UNKNOWN fail_streak=0 threshold=$FailThreshold reason=no_output"
}

Add-Content -Path $outLog -Value ("{0} exit={1} {2}" -f $ts, $exitCode, $last)

exit $exitCode
