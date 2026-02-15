# Phase1 OFF 3-round test (PowerShell)
# Uses Invoke-WebRequest. Run after: $env:PHASE1_REFLECTION = "off"; python unified_api_server.py
# In another terminal: .\phase1_run_off_3rounds.ps1

$ErrorActionPreference = "Stop"
try {
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
} catch {}
Set-Location $PSScriptRoot
$unifiedApiBaseUrl = if ($env:MANAOS_INTEGRATION_API_URL) { $env:MANAOS_INTEGRATION_API_URL.TrimEnd('/') } else { "http://127.0.0.1:9502" }
$api = "$unifiedApiBaseUrl/api/llm/chat"
$timeout = 300

Write-Host "=== Phase1 OFF 3-round test ===" -ForegroundColor Cyan
Write-Host ""

$threadId = $null
$history = @()

for ($i = 1; $i -le 3; $i++) {
    $userMsg = "Test round $i"
    $msg = @{ "role" = "user"; "content" = $userMsg }
    $history += @(, $msg)
    $bodyObj = @{ "messages" = $history }
    if ($threadId) { $bodyObj["thread_id"] = $threadId }
    $body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

    Write-Host "[Round $i] user: $userMsg"
    try {
        $r = Invoke-WebRequest -Uri $api -Method POST -Body $body `
            -ContentType "application/json; charset=utf-8" -UseBasicParsing -TimeoutSec $timeout
        $resp = $r.Content | ConvertFrom-Json
        $fullContent = $resp.response
        if (-not $fullContent -and $resp.message) { $fullContent = $resp.message.content }
        $respText = $fullContent
        if ($respText.Length -gt 50) { $respText = $respText.Substring(0, 50) + "..." }
        $astMsg = @{ "role" = "assistant"; "content" = $fullContent }
        $history += @(, $astMsg)
        $threadId = $resp.thread_id
        Write-Host "         assistant: $respText"
        if ($threadId) { Write-Host "         thread_id=$($threadId.Substring(0, [Math]::Min(8, $threadId.Length)))..." }
    } catch {
        Write-Host "API Error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "--- Aggregate (phase1_aggregate.py) ---" -ForegroundColor Cyan
Write-Host ""
python phase1_aggregate.py
