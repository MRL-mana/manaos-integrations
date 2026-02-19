param(
    [string]$ReportPath = "",
    [string]$ManualRecordPath = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportDir = Join-Path $scriptDir "Reports"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$createdAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Resolve-LatestFile {
    param(
        [string]$Dir,
        [string]$Filter,
        [string]$InputPath
    )

    if ($InputPath -and (Test-Path $InputPath)) {
        return (Resolve-Path $InputPath).Path
    }

    $latest = Get-ChildItem -Path $Dir -Filter $Filter -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        throw "No file found with filter: $Filter"
    }

    return $latest.FullName
}

$resolvedReportPath = Resolve-LatestFile -Dir $reportDir -Filter "OpenWebUI_Tool_Acceptance_Report_*.md" -InputPath $ReportPath
$resolvedManualPath = Resolve-LatestFile -Dir $reportDir -Filter "OpenWebUI_Manual_Case_Record_*.json" -InputPath $ManualRecordPath

$reportText = Get-Content -Path $resolvedReportPath -Raw -Encoding UTF8
$manual = Get-Content -Path $resolvedManualPath -Raw -Encoding UTF8 | ConvertFrom-Json

$automatedOverall = "UNKNOWN"
$automatedChecks = "0/0"

$overallMatch = [regex]::Match($reportText, "\*\*Overall\*\*:\s*([A-Z]+)")
if ($overallMatch.Success) {
    $automatedOverall = $overallMatch.Groups[1].Value
}

$checksMatch = [regex]::Match($reportText, "\*\*Automated checks\*\*:\s*([0-9]+\s*/\s*[0-9]+)")
if ($checksMatch.Success) {
    $automatedChecks = $checksMatch.Groups[1].Value
}

$manualVerdict = $manual.verdict
$manualCases = $manual.cases

$finalVerdict = "PENDING"
if ($automatedOverall -eq "PASS" -and $manualVerdict -eq "PASS") {
    $finalVerdict = "PASS"
}
elseif ($automatedOverall -eq "FAIL" -or $manualVerdict -eq "FAIL") {
    $finalVerdict = "FAIL"
}

$summaryMdPath = Join-Path $reportDir ("OpenWebUI_Tool_Acceptance_Final_{0}.md" -f $timestamp)
$summaryJsonPath = Join-Path $reportDir ("OpenWebUI_Tool_Acceptance_Final_{0}.json" -f $timestamp)

$summaryMd = @"
# OpenWebUI Tool Acceptance Final Summary

**Created at**: $createdAt  
**Final verdict**: $finalVerdict

## Inputs

- Automated report: $resolvedReportPath
- Manual record: $resolvedManualPath

## Automated Check Summary

- Overall: $automatedOverall
- Checks: $automatedChecks

## Manual Check Summary

- Verdict: $manualVerdict
- Case1: $($manualCases.case1)
- Case2: $($manualCases.case2)
- Case3: $($manualCases.case3)
- Case4: $($manualCases.case4)
- Notes: $($manual.notes)

## Next Action

$(if ($finalVerdict -eq "PASS") {
"- Deployment-ready acceptance state confirmed."
} elseif ($finalVerdict -eq "FAIL") {
"- Investigate failed checks and re-run acceptance flow."
} else {
"- Execute remaining manual chat cases, then re-run finalization."
})
"@

Set-Content -Path $summaryMdPath -Value $summaryMd -Encoding UTF8

$summaryObj = [PSCustomObject]@{
    created_at = $createdAt
    final_verdict = $finalVerdict
    automated = [ordered]@{
        report_path = $resolvedReportPath
        overall = $automatedOverall
        checks = $automatedChecks
    }
    manual = [ordered]@{
        record_path = $resolvedManualPath
        verdict = $manualVerdict
        cases = $manualCases
        notes = $manual.notes
    }
}

$summaryObj | ConvertTo-Json -Depth 8 | Set-Content -Path $summaryJsonPath -Encoding UTF8

Write-Host "[OK] Final summary markdown: $summaryMdPath" -ForegroundColor Green
Write-Host "[OK] Final summary json: $summaryJsonPath" -ForegroundColor Green
