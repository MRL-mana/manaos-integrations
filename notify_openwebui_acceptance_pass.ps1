param(
    [string]$ReportDir = "",
    [switch]$WriteStatusFile
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ReportDir) {
    $ReportDir = Join-Path $scriptDir "Reports"
}

if (-not (Test-Path $ReportDir)) {
    Write-Host "[WARN] report_dir_missing status=UNKNOWN dir=$ReportDir" -ForegroundColor Yellow
    exit 0
}

$latest = Get-ChildItem -Path $ReportDir -Filter "OpenWebUI_Tool_Acceptance_Final_*.json" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    Write-Host "[WARN] acceptance_status=UNKNOWN reason=no_final_summary" -ForegroundColor Yellow
    exit 0
}

$summary = Get-Content -Path $latest.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$verdict = [string]$summary.final_verdict
$createdAt = [string]$summary.created_at

$statusLine = "acceptance_status=$verdict created_at=$createdAt file=$($latest.Name)"

if ($WriteStatusFile) {
    $statusFile = Join-Path $ReportDir "OpenWebUI_Acceptance_Latest_Status.txt"
    Set-Content -Path $statusFile -Value $statusLine -Encoding UTF8
}

switch ($verdict) {
    "PASS" {
        Write-Host "[PASS] $statusLine" -ForegroundColor Green
        exit 0
    }
    "FAIL" {
        Write-Host "[INFO] $statusLine" -ForegroundColor Red
        exit 0
    }
    default {
        Write-Host "[INFO] $statusLine" -ForegroundColor Yellow
        exit 0
    }
}
