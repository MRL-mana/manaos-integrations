$ErrorActionPreference = "Continue"

Write-Host "=== Open WebUI x ManaOS Acceptance Smoke ===" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Write-Ok($msg) { Write-Host "[OK]  $msg" -ForegroundColor Green }
function Write-WarnMsg($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Ng($msg) { Write-Host "[NG]  $msg" -ForegroundColor Red }

function Test-Http {
    param(
        [string]$Url,
        [int]$TimeoutSec = 5
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec $TimeoutSec
        return @{ ok = $true; status = [int]$response.StatusCode }
    }
    catch {
        return @{ ok = $false; status = 0; error = $_.Exception.Message }
    }
}

$optionalEnsureScript = Join-Path $scriptDir "ensure_optional_services.ps1"
if (Test-Path $optionalEnsureScript) {
    Write-Host "`n[0/4] Ensure optional services" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $optionalEnsureScript | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Ng ("optional services ensure failed (exit={0})" -f $LASTEXITCODE)
    }
}
else {
    Write-WarnMsg "ensure_optional_services.ps1 not found, skipping"
}

Write-Host "`n[1/4] Run full startup" -ForegroundColor Cyan
$fullStart = Join-Path $scriptDir "start_openwebui_manaos_full.ps1"
if (Test-Path $fullStart) {
    powershell -ExecutionPolicy Bypass -File $fullStart | Out-Host
}
else {
    Write-WarnMsg "start_openwebui_manaos_full.ps1 not found, skipping"
}

Write-Host "`n[2/4] Check critical endpoints" -ForegroundColor Cyan
$checks = @(
    @{ name = "Tool Server Health"; url = "http://127.0.0.1:9503/health" },
    @{ name = "Tool Server OpenAPI"; url = "http://127.0.0.1:9503/openapi.json" },
    @{ name = "Unified API Health"; url = "http://127.0.0.1:9502/health" },
    @{ name = "Open WebUI"; url = "http://127.0.0.1:3001" }
)

$failed = 0
foreach ($item in $checks) {
    $result = Test-Http -Url $item.url
    if ($result.ok) {
        Write-Ok ("{0} ({1})" -f $item.name, $result.status)
    }
    else {
        $failed++
        Write-Ng ("{0} ({1})" -f $item.name, $result.error)
    }
}

Write-Host "`n[2.5/4] Run auto-local sanity test" -ForegroundColor Cyan
$autoLocalTest = Join-Path $scriptDir "test_auto_local_chat.ps1"
if (Test-Path $autoLocalTest) {
    $autoLocalLines = powershell -NoProfile -ExecutionPolicy Bypass -File $autoLocalTest -RequestTimeoutSec 360 -MaxRetries 4 -WarmupTimeoutSec 60 2>&1
    $autoLocalLines | Out-Host

    $autoLocalText = ($autoLocalLines | Out-String)
    if ($LASTEXITCODE -eq 0 -and $autoLocalText -match "(?m)^status=OK\s*$") {
        Write-Ok "auto-local sanity test passed"
    }
    else {
        $failed++
        Write-Ng ("auto-local sanity test failed (exit={0})" -f $LASTEXITCODE)
    }
}
else {
    $failed++
    Write-Ng "auto-local test file not found"
}

Write-Host "`n[3/4] Run Tool Server integration test" -ForegroundColor Cyan
$integrationTest = Join-Path $scriptDir "tests\integration\test_tool_server_integration.py"
if (Test-Path $integrationTest) {
    py -3.10 $integrationTest | Out-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Integration test passed"
    }
    else {
        $failed++
        Write-Ng ("Integration test failed (exit={0})" -f $LASTEXITCODE)
    }
}
else {
    $failed++
    Write-Ng "Integration test file not found"
}

Write-Host "`n[4/4] Manual chat acceptance prompts" -ForegroundColor Cyan
Write-Host "Run these in Open WebUI:" -ForegroundColor White
Write-Host "  1) Check service status -> service_status" -ForegroundColor Gray
Write-Host "  2) Open README file -> vscode_open_file" -ForegroundColor Gray
Write-Host "  3) Execute Get-Location -> execute_command (allowed)" -ForegroundColor Gray
Write-Host "  4) Execute Remove-Item -> execute_command (blocked)" -ForegroundColor Gray

$securityLog = Join-Path $scriptDir "logs\tool_server_security.log"
if (Test-Path $securityLog) {
    Write-Ok ("Audit log found: {0}" -f $securityLog)
    Get-Content -Path $securityLog -Tail 5 | Out-Host
}
else {
    Write-WarnMsg "Audit log not found yet"
}

Write-Host "`n=== Acceptance Smoke Completed ===" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Ok "All automated checks passed"
    exit 0
}

Write-Ng ("Failure count: {0}" -f $failed)
exit 1
