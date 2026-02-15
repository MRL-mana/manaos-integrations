# Phase1 拡張実験（30往復）
# ON: $env:PHASE1_REFLECTION = "on"; python unified_api_server.py
# OFF: $env:PHASE1_REFLECTION = "off"; python unified_api_server.py
# 実行: .\phase1_run_extended.ps1 -Condition on または -Condition off
# デフォルト: 30往復

param(
    [ValidateSet("on", "off")]
    [string]$Condition = "on",
    [int]$Rounds = 30
)

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

Write-Host "=== Phase1 $Condition $Rounds-round extended test ===" -ForegroundColor Cyan
Write-Host ""

$threadId = $null
$history = @()

for ($i = 1; $i -le $Rounds; $i++) {
    $userMsg = "Round $i. Brief question."
    $msg = @{ "role" = "user"; "content" = $userMsg }
    $history += @(, $msg)
    $bodyObj = @{ "messages" = $history }
    if ($threadId) { $bodyObj["thread_id"] = $threadId }
    $body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

    Write-Host "[$i/$Rounds]"
    try {
        $r = Invoke-WebRequest -Uri $api -Method POST -Body $body `
            -ContentType "application/json; charset=utf-8" -UseBasicParsing -TimeoutSec $timeout
        $resp = $r.Content | ConvertFrom-Json
        $fullContent = $resp.response
        if (-not $fullContent -and $resp.message) { $fullContent = $resp.message.content }
        $astMsg = @{ "role" = "assistant"; "content" = $fullContent }
        $history += @(, $astMsg)
        $threadId = $resp.thread_id
        if ($Condition -eq "on") { Start-Sleep -Seconds 4 }
    } catch {
        Write-Host "API Error round $i : $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "--- Aggregate ---" -ForegroundColor Cyan
python phase1_aggregate.py
