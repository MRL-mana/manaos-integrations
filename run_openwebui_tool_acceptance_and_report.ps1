$ErrorActionPreference = "Continue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportDir = Join-Path $scriptDir "Reports"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (-not (Test-Path $reportDir)) {
    New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
}

$acceptanceScript = Join-Path $scriptDir "run_openwebui_tool_acceptance.ps1"
$rawLogPath = Join-Path $reportDir ("OpenWebUI_Tool_Acceptance_Raw_{0}.log" -f $timestamp)
$reportPath = Join-Path $reportDir ("OpenWebUI_Tool_Acceptance_Report_{0}.md" -f $timestamp)

if (-not (Test-Path $acceptanceScript)) {
    Write-Host "[NG] Acceptance script not found: $acceptanceScript" -ForegroundColor Red
    exit 1
}

Write-Host "=== Run acceptance and generate report ===" -ForegroundColor Cyan
Write-Host "[INFO] Running: $acceptanceScript" -ForegroundColor Gray

$output = & powershell -ExecutionPolicy Bypass -File $acceptanceScript 2>&1 | Tee-Object -FilePath $rawLogPath
$acceptanceExitCode = $LASTEXITCODE

function Test-OutputLine {
    param([string]$Pattern)
    return ($output | Select-String -Pattern $Pattern -SimpleMatch -Quiet)
}

$checks = @(
    @{ Name = "Tool Server Health"; Pattern = "[OK]  Tool Server Health (200)" },
    @{ Name = "Tool Server OpenAPI"; Pattern = "[OK]  Tool Server OpenAPI (200)" },
    @{ Name = "Unified API Health"; Pattern = "[OK]  Unified API Health (200)" },
    @{ Name = "Open WebUI"; Pattern = "[OK]  Open WebUI (200)" },
    @{ Name = "Integration test"; Pattern = "[OK]  Integration test passed" },
    @{ Name = "Automated checks summary"; Pattern = "[OK]  All automated checks passed" }
)

$checkResults = foreach ($c in $checks) {
    $ok = Test-OutputLine -Pattern $c.Pattern
    [PSCustomObject]@{
        Name = $c.Name
        Ok = $ok
    }
}

$passedCount = ($checkResults | Where-Object { $_.Ok }).Count
$totalCount = $checkResults.Count

$securityLogPath = Join-Path $scriptDir "logs\tool_server_security.log"
$securityTail = @()
if (Test-Path $securityLogPath) {
    $securityTail = Get-Content -Path $securityLogPath -Tail 5
}

$overallStatus = if ($acceptanceExitCode -eq 0) { "PASS" } else { "FAIL" }
$createdAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$resultLines = foreach ($r in $checkResults) {
    if ($r.Ok) {
        "- [OK] **{0}**" -f $r.Name
    }
    else {
        "- [NG] **{0}**" -f $r.Name
    }
}

$securityLines = if ($securityTail.Count -gt 0) {
    ($securityTail | ForEach-Object { "- {0}" -f $_ }) -join "`n"
}
else {
    "- (no log lines)"
}

$manualCases = @(
    "- [ ] Case 1: service_status is called from chat",
    "- [ ] Case 2: vscode_open_file opens target file",
    "- [ ] Case 3: execute_command allows Get-Location",
    "- [ ] Case 4: execute_command blocks Remove-Item"
) -join "`n"

$report = @"
# OpenWebUI Tool Acceptance Report

**Created at**: $createdAt  
**Overall**: $overallStatus  
**Automated checks**: $passedCount / $totalCount  
**Acceptance exit code**: $acceptanceExitCode

## Automated Result

$($resultLines -join "`n")

## Manual Chat Cases (Open WebUI)

$manualCases

## Security Audit Tail

$securityLines

## Artifacts

- Raw log: $rawLogPath
- Security log: $securityLogPath
"@

Set-Content -Path $reportPath -Value $report -Encoding UTF8

Write-Host "[OK] Report generated: $reportPath" -ForegroundColor Green
Write-Host "[OK] Raw log saved: $rawLogPath" -ForegroundColor Green

exit $acceptanceExitCode
