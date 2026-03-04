#!/usr/bin/env pwsh
# ============================================================
# step_deep_research/start_server.ps1
# Step-Deep-Research API サーバー起動スクリプト
# ============================================================
# 使い方:
#   .\step_deep_research\start_server.ps1              # フォアグラウンド
#   .\step_deep_research\start_server.ps1 -Bg          # バックグラウンド
#   .\step_deep_research\start_server.ps1 -Check       # ヘルスチェックのみ
# ============================================================

param(
    [switch]$Bg,
    [switch]$Check
)

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ROOT

$PORT = 5120
$URL  = "http://127.0.0.1:$PORT"

function Test-Running {
    try {
        $r = Invoke-RestMethod "$URL/health" -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

if ($Check) {
    if (Test-Running) {
        Write-Host "  ✓ Step-Deep-Research は稼働中 ($URL)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Step-Deep-Research はオフライン ($URL)" -ForegroundColor Red
    }
    exit 0
}

if (Test-Running) {
    Write-Host "  ✓ すでに稼働中 ($URL)" -ForegroundColor Green
    exit 0
}

Write-Host "  ► Step-Deep-Research API 起動中 (port $PORT)..." -ForegroundColor Cyan

$env:PYTHONPATH = "$ROOT;$ROOT\scripts\misc"
$pyArgs = @("-u", "$ROOT\step_deep_research\api_server.py")

if ($Bg) {
    $proc = Start-Process py.exe -ArgumentList (@("-3.10") + $pyArgs) `
        -RedirectStandardOutput "$ROOT\logs\step_deep_research.stdout.log" `
        -RedirectStandardError  "$ROOT\logs\step_deep_research.stderr.log" `
        -WindowStyle Hidden -PassThru
    Write-Host "  ✓ バックグラウンド起動 PID=$($proc.Id)" -ForegroundColor Green
    Write-Host "    ログ: logs\step_deep_research.stdout.log"
    
    # 起動確認ループ
    $waited = 0
    while ($waited -lt 15) {
        Start-Sleep 2
        $waited += 2
        if (Test-Running) {
            Write-Host "  ✓ 起動完了 - $URL" -ForegroundColor Green
            exit 0
        }
    }
    Write-Host "  ⚠ 15秒待ったが応答なし。ログを確認してください。" -ForegroundColor Yellow
} else {
    & py.exe -3.10 @pyArgs
}
