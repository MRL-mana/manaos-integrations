param(
    [ValidateSet("pass", "fail", "skip")]
    [string]$Case1 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case2 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case3 = "skip",

    [ValidateSet("pass", "fail", "skip")]
    [string]$Case4 = "skip",

    [string]$Notes = "",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportDir = Join-Path $scriptDir "Reports"

function Resolve-ReportPath {
    param([string]$InputPath)

    if ($InputPath -and (Test-Path $InputPath)) {
        return (Resolve-Path $InputPath).Path
    }

    $latest = Get-ChildItem -Path $reportDir -Filter "OpenWebUI_Tool_Acceptance_Report_*.md" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        throw "No acceptance report found in Reports directory."
    }

    return $latest.FullName
}

function Get-ManualVerdict {
    param(
        [string]$S1,
        [string]$S2,
        [string]$S3,
        [string]$S4
    )

    $all = @($S1, $S2, $S3, $S4)
    if ($all -contains "fail") {
        return "FAIL"
    }
    if (($all | Where-Object { $_ -eq "pass" }).Count -eq 4) {
        return "PASS"
    }
    return "PENDING"
}

function To-ChecklistMark {
    param([string]$Status)

    if ($Status -eq "pass") {
        return "x"
    }
    return " "
}

$resolvedReportPath = Resolve-ReportPath -InputPath $ReportPath
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$recordedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$verdict = Get-ManualVerdict -S1 $Case1 -S2 $Case2 -S3 $Case3 -S4 $Case4

$entry = @"

## Manual Validation Record

**Recorded at**: $recordedAt  
**Manual verdict**: $verdict

- [$(To-ChecklistMark -Status $Case1)] Case 1: service_status is called from chat ($($Case1.ToUpper()))
- [$(To-ChecklistMark -Status $Case2)] Case 2: vscode_open_file opens target file ($($Case2.ToUpper()))
- [$(To-ChecklistMark -Status $Case3)] Case 3: execute_command allows Get-Location ($($Case3.ToUpper()))
- [$(To-ChecklistMark -Status $Case4)] Case 4: execute_command blocks Remove-Item ($($Case4.ToUpper()))

**Operator notes**: $(if ($Notes) { $Notes } else { "(none)" })
"@

Add-Content -Path $resolvedReportPath -Value $entry -Encoding UTF8

$artifact = [PSCustomObject]@{
    recorded_at = $recordedAt
    report_path = $resolvedReportPath
    verdict = $verdict
    cases = [ordered]@{
        case1 = $Case1
        case2 = $Case2
        case3 = $Case3
        case4 = $Case4
    }
    notes = $Notes
}

$artifactPath = Join-Path $reportDir ("OpenWebUI_Manual_Case_Record_{0}.json" -f $timestamp)
$artifact | ConvertTo-Json -Depth 5 | Set-Content -Path $artifactPath -Encoding UTF8

Write-Host "[OK] Manual record appended: $resolvedReportPath" -ForegroundColor Green
Write-Host "[OK] Manual record artifact: $artifactPath" -ForegroundColor Green
