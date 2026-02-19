param(
    [switch]$RequirePass
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$recordScript = Join-Path $scriptDir "record_openwebui_manual_cases.ps1"
$finalizeScript = Join-Path $scriptDir "finalize_openwebui_acceptance.ps1"
$checkScript = Join-Path $scriptDir "check_latest_openwebui_acceptance.ps1"

if (-not (Test-Path $recordScript)) {
    throw "record_openwebui_manual_cases.ps1 not found"
}
if (-not (Test-Path $finalizeScript)) {
    throw "finalize_openwebui_acceptance.ps1 not found"
}
if (-not (Test-Path $checkScript)) {
    throw "check_latest_openwebui_acceptance.ps1 not found"
}

function Read-CaseResult {
    param(
        [string]$Label,
        [string]$DefaultValue = "skip"
    )

    while ($true) {
        $inputValue = Read-Host "$Label (pass/fail/skip) [default: $DefaultValue]"
        if ([string]::IsNullOrWhiteSpace($inputValue)) {
            return $DefaultValue
        }

        $normalized = $inputValue.Trim().ToLowerInvariant()
        if ($normalized -in @("pass", "fail", "skip")) {
            return $normalized
        }

        Write-Host "[WARN] Invalid input. Use pass/fail/skip." -ForegroundColor Yellow
    }
}

Write-Host "=== OpenWebUI Manual Acceptance (Interactive) ===" -ForegroundColor Cyan
Write-Host "Enter results after running the 4 manual chat cases in OpenWebUI." -ForegroundColor Gray

$case1 = Read-CaseResult -Label "Case1 service_status"
$case2 = Read-CaseResult -Label "Case2 vscode_open_file"
$case3 = Read-CaseResult -Label "Case3 execute_command allowed"
$case4 = Read-CaseResult -Label "Case4 execute_command blocked"
$notes = Read-Host "Notes (optional)"

Write-Host ""
Write-Host "[1/3] Record manual cases" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $recordScript -Case1 $case1 -Case2 $case2 -Case3 $case3 -Case4 $case4 -Notes $notes
if ($LASTEXITCODE -ne 0) {
    throw "Manual case recording failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[2/3] Finalize acceptance" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $finalizeScript
if ($LASTEXITCODE -ne 0) {
    throw "Finalization failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[3/3] Show latest verdict" -ForegroundColor Cyan
if ($RequirePass) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $checkScript -RequirePass
}
else {
    powershell -NoProfile -ExecutionPolicy Bypass -File $checkScript
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[OK] Interactive manual acceptance completed" -ForegroundColor Green
