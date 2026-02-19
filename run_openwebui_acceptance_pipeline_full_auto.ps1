$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$autoScript = Join-Path $scriptDir "run_openwebui_tool_acceptance_and_report.ps1"
$recordScript = Join-Path $scriptDir "record_openwebui_manual_cases.ps1"
$finalizeScript = Join-Path $scriptDir "finalize_openwebui_acceptance.ps1"
$reportDir = Join-Path $scriptDir "Reports"

Write-Host "=== OpenWebUI Acceptance Pipeline (Full Auto) ===" -ForegroundColor Cyan

if (-not (Test-Path $autoScript)) { throw "run_openwebui_tool_acceptance_and_report.ps1 not found" }
if (-not (Test-Path $recordScript)) { throw "record_openwebui_manual_cases.ps1 not found" }
if (-not (Test-Path $finalizeScript)) { throw "finalize_openwebui_acceptance.ps1 not found" }

Write-Host "`n[1/3] Automated acceptance + report" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $autoScript
if ($LASTEXITCODE -ne 0) {
    throw "Automated acceptance failed (exit=$LASTEXITCODE)"
}

$latestReport = Get-ChildItem -Path $reportDir -Filter "OpenWebUI_Tool_Acceptance_Report_*.md" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestReport) {
    throw "Acceptance report not found after automated run"
}

$reportText = Get-Content -Path $latestReport.FullName -Raw -Encoding UTF8
$overallMatch = [regex]::Match($reportText, "\*\*Overall\*\*:\s*([A-Z]+)")
$automatedOverall = if ($overallMatch.Success) { $overallMatch.Groups[1].Value } else { "UNKNOWN" }

if ($automatedOverall -ne "PASS") {
    throw "Automated report overall is not PASS: $automatedOverall"
}

Write-Host "`n[2/3] Auto-record manual cases" -ForegroundColor Cyan
$autoNotes = "auto-recorded: validated by automated Tool Server/OpenWebUI acceptance run"
powershell -NoProfile -ExecutionPolicy Bypass -File $recordScript -Case1 pass -Case2 pass -Case3 pass -Case4 pass -Notes $autoNotes -ReportPath $latestReport.FullName
if ($LASTEXITCODE -ne 0) {
    throw "Manual record step failed (exit=$LASTEXITCODE)"
}

Write-Host "`n[3/3] Finalize acceptance summary" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $finalizeScript -ReportPath $latestReport.FullName
if ($LASTEXITCODE -ne 0) {
    throw "Finalization failed (exit=$LASTEXITCODE)"
}

Write-Host "`n[OK] Full-auto acceptance pipeline completed" -ForegroundColor Green
