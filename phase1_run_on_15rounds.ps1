# Phase1 ON 15-round test (PowerShell)
# Server must be started with: $env:PHASE1_REFLECTION = "on"; python unified_api_server.py
# In another terminal: .\phase1_run_on_15rounds.ps1
# Or specify rounds: .\phase1_run_on_15rounds.ps1 -Rounds 20
# Optional: clear logs before run for clean ON-only data:
#   Remove-Item phase1_conversation.log, phase1_reflection.log -ErrorAction SilentlyContinue

param([int]$Rounds = 15)

$ErrorActionPreference = "Stop"
try {
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
} catch {}
Set-Location $PSScriptRoot
$api = "http://127.0.0.1:9500/api/llm/chat"
$timeout = 300

Write-Host "=== Phase1 ON $Rounds-round test ===" -ForegroundColor Cyan
Write-Host ""

$threadId = $null
$history = @()

for ($i = 1; $i -le $Rounds; $i++) {
    $userMsg = "Round $i. What can you help me with?"
    $msg = @{ "role" = "user"; "content" = $userMsg }
    $history += @(, $msg)
    $bodyObj = @{ "messages" = $history }
    if ($threadId) { $bodyObj["thread_id"] = $threadId }
    $body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

    Write-Host "[$i/$Rounds] user: $userMsg"
    try {
        $r = Invoke-WebRequest -Uri $api -Method POST -Body $body `
            -ContentType "application/json; charset=utf-8" -UseBasicParsing -TimeoutSec $timeout
        $resp = $r.Content | ConvertFrom-Json
        $fullContent = $resp.response
        if (-not $fullContent -and $resp.message) { $fullContent = $resp.message.content }
        $respText = $fullContent
        if ($respText.Length -gt 40) { $respText = $respText.Substring(0, 40) + "..." }
        $astMsg = @{ "role" = "assistant"; "content" = $fullContent }
        $history += @(, $astMsg)
        $threadId = $resp.thread_id
        Write-Host "         assistant: $respText"
    } catch {
        Write-Host "API Error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "--- Aggregate (phase1_aggregate.py) ---" -ForegroundColor Cyan
Write-Host ""
python phase1_aggregate.py
