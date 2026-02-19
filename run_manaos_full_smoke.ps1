$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$results = [ordered]@{}

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
    python .\check_services_health.py | Out-Host
}

Invoke-Step -Name "OpenAI Router Models" -Action {
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:5211/v1/models" -Method Get -TimeoutSec 5
    if (-not $models.data) {
        throw "No models returned"
    }
    $models.data | Select-Object -First 5 id | Format-Table -AutoSize | Out-Host
}

Invoke-Step -Name "auto-local Chat" -Action {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\test_auto_local_chat.ps1 | Out-Host
}

Invoke-Step -Name "Tool Server Integration" -Action {
    python .\tests\integration\test_tool_server_integration.py | Out-Host
}

Write-Host "`n========================================="
Write-Host "ManaOS Full Smoke Summary"
Write-Host "========================================="

$passed = 0
$total = $results.Count
foreach ($key in $results.Keys) {
    if ($results[$key]) {
        $passed++
        Write-Host "[OK] $key" -ForegroundColor Green
    }
    else {
        Write-Host "[NG] $key" -ForegroundColor Red
    }
}

Write-Host "Result: $passed / $total"

if ($passed -ne $total) {
    exit 1
}
