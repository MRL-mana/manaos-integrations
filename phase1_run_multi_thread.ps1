# Phase1 複数スレッド実験（同一テーマ再訪の計測用）
# 異なるテーマの会話を複数スレッドで実行。phase1_aggregate でテーマ再訪を確認。
# 事前: API起動（OFF推奨・速い）
# 実行: .\phase1_run_multi_thread.ps1

$ErrorActionPreference = "Stop"
try {
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    $OutputEncoding = [System.Text.UTF8Encoding]::new()
} catch {}
Set-Location $PSScriptRoot
$api = "http://127.0.0.1:9500/api/llm/chat"
$timeout = 120

# 同一テーマ再訪: 1と4が天気、2と5がプログラミング、3が料理 → 2テーマ再訪
$themes = @(
    "今日の天気と明日の予報について教えて",
    "Pythonプログラミングの勉強方法を教えて",
    "簡単な料理のレシピを教えて",
    "今日の天気と明日の予報について教えて",
    "Pythonプログラミングの勉強方法を教えて"
)

Write-Host "=== Phase1 Multi-thread ($($themes.Count) threads) ===" -ForegroundColor Cyan
Start-Sleep -Seconds 5

foreach ($i in 1..$themes.Count) {
    $firstMsg = $themes[$i - 1]
    $msg = @{ "role" = "user"; "content" = $firstMsg }
    $bodyObj = @{ "messages" = @(, $msg) }
    $body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

    Write-Host "[Thread $i] $firstMsg"
    try {
        $r = Invoke-WebRequest -Uri $api -Method POST -Body $body `
            -ContentType "application/json; charset=utf-8" -UseBasicParsing -TimeoutSec $timeout
        $resp = $r.Content | ConvertFrom-Json
        $tid = $resp.thread_id
        Write-Host "         thread_id=$($tid.Substring(0, [Math]::Min(8, $tid.Length)))..."
    } catch {
        Write-Host "API Error: $_" -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "--- Aggregate ---" -ForegroundColor Cyan
python phase1_aggregate.py
