$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$results = [ordered]@{}

function Get-CompactLabel {
    param(
        [string]$Text,
        [int]$MaxLength = 24
    )

    if ([string]::IsNullOrEmpty($Text)) {
        return ""
    }
    if ($Text.Length -le $MaxLength) {
        return $Text
    }
    if ($MaxLength -le 1) {
        return $Text.Substring(0, 1)
    }
    return $Text.Substring(0, $MaxLength - 1) + "…"
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    try {
        & $Action
        $results[$Name] = $true
        Write-Host "[OK] $Name" -ForegroundColor Green
    }
    catch {
        $results[$Name] = $false
        Write-Host "[NG] ${Name}: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Invoke-Step -Name "ManaOS Core Health" -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ensure_optional_services.ps1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Optional services recovery failed (exit=$LASTEXITCODE)"
    }

    python .\check_services_health.py | Out-Host
}

Invoke-Step -Name "OpenAI Router Models" -Action {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/models" -Method Get -TimeoutSec 5
    if (-not $models.data) {
        throw "No models returned"
    }
    $modelIds = @($models.data | ForEach-Object { $_.id })
    if (-not ($modelIds -contains "auto-local")) {
        throw "Required model 'auto-local' is not available"
    }
    $models.data | Select-Object -First 5 id | Format-Table -AutoSize | Out-Host
}

Invoke-Step -Name "auto-local Chat" -Action {
    $chatLines = powershell -NoProfile -ExecutionPolicy Bypass -File .\test_auto_local_chat.ps1 -RequestTimeoutSec 360 -MaxRetries 4 -WarmupTimeoutSec 60 2>&1
    $chatLines | Out-Host

    $chatText = ($chatLines | Out-String)
    if ($chatText -notmatch "(?m)^status=OK\s*$") {
        throw "auto-local chat did not report status=OK"
    }
}

Invoke-Step -Name "Tool Server Integration" -Action {
    $toolLines = python .\tests\integration\test_tool_server_integration.py 2>&1
    $toolLines | Out-Host

    $toolText = ($toolLines | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "Tool Server integration test exited with code $LASTEXITCODE"
    }
    if ($toolText -match "(?m)^\[NG\]\s") {
        throw "Tool Server integration output contains [NG] markers"
    }
    if ($toolText -match "(?m)^\[WARNING\]\s") {
        throw "Tool Server integration reports failed test cases"
    }
}

Write-Host "`n========================================="
Write-Host "ManaOS Full Smoke Summary"
Write-Host "========================================="
Write-Host "Status | Check"
Write-Host "-----------------------------------------"

$passed = 0
$total = $results.Count
foreach ($key in $results.Keys) {
    $label = Get-CompactLabel -Text $key -MaxLength 24
    if ($results[$key]) {
        $passed++
        Write-Host ("OK     | {0}" -f $label) -ForegroundColor Green
    }
    else {
        Write-Host ("NG     | {0}" -f $label) -ForegroundColor Red
    }
}

$rate = if ($total -gt 0) { [math]::Round(($passed / $total) * 100, 1) } else { 0 }
Write-Host "-----------------------------------------"
Write-Host ("Result | {0}/{1} ({2}%)" -f $passed, $total, $rate)

if ($passed -ne $total) {
    exit 1
}
