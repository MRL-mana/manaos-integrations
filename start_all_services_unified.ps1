# ManaOS統合システム 全サービス起動スクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ManaOS統合システム 全サービス起動" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# n8n Webhook URLを設定
$env:N8N_WEBHOOK_URL = "http://100.93.120.33:5678/webhook/comfyui-generated"
Write-Host "[INFO] n8n Webhook URLを設定しました" -ForegroundColor Gray
Write-Host "  URL: $env:N8N_WEBHOOK_URL" -ForegroundColor Gray
Write-Host ""

# 1. ComfyUI起動確認
Write-Host "[1] ComfyUI起動確認..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8188/system_stats" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "   [OK] ComfyUIは起動中です" -ForegroundColor Green
    } else {
        Write-Host "   [WARN] ComfyUIが起動していません" -ForegroundColor Yellow
        Write-Host "   起動: .\start_comfyui_local.ps1" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [WARN] ComfyUIが起動していません" -ForegroundColor Yellow
    Write-Host "   起動: .\start_comfyui_local.ps1" -ForegroundColor Gray
}
Write-Host ""

# 2. 統合APIサーバー起動
Write-Host "[2] 統合APIサーバーを起動します..." -ForegroundColor Yellow
$apiServerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*unified_api_server.py*" -or 
    (Get-NetTCPConnection -LocalPort 9500 -ErrorAction SilentlyContinue)
}

if ($apiServerProcess -or (Get-NetTCPConnection -LocalPort 9500 -ErrorAction SilentlyContinue)) {
    Write-Host "   [OK] 統合APIサーバーは既に起動中です" -ForegroundColor Green
} else {
    Write-Host "   統合APIサーバーを起動中..." -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir'; `$env:N8N_WEBHOOK_URL='http://100.93.120.33:5678/webhook/comfyui-generated'; python unified_api_server.py" -WindowStyle Normal
    Write-Host "   [OK] 統合APIサーバーを起動しました（別ウィンドウ）" -ForegroundColor Green
    Write-Host "   数秒待ってからテストを実行してください" -ForegroundColor Gray
    Start-Sleep -Seconds 8
}
Write-Host ""

# 3. 動作確認
Write-Host "[3] 動作確認..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:9500/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "   [OK] 統合APIサーバーは正常に動作しています" -ForegroundColor Green
        
        # 統合システム状態を表示
        $statusResponse = Invoke-RestMethod -Uri "http://localhost:9500/api/integrations/status" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($statusResponse) {
            Write-Host ""
            Write-Host "   統合システム状態:" -ForegroundColor Gray
            $systems = @("comfyui", "civitai", "google_drive", "obsidian")
            foreach ($sys in $systems) {
                $sysStatus = $statusResponse.$sys
                if ($sysStatus -and $sysStatus.available) {
                    Write-Host "     [OK] $sys : 利用可能" -ForegroundColor Green
                } else {
                    Write-Host "     [NG] $sys : 利用不可" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "   [WARN] 統合APIサーバーに接続できません" -ForegroundColor Yellow
        Write-Host "   もう少し待ってから再試行してください" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [WARN] 統合APIサーバーに接続できません" -ForegroundColor Yellow
    Write-Host "   もう少し待ってから再試行してください" -ForegroundColor Gray
}
Write-Host ""

# 4. 次のステップ
Write-Host "[4] 次のステップ..." -ForegroundColor Yellow
Write-Host "   完全統合テストを実行:" -ForegroundColor Cyan
Write-Host "     python complete_integration_test.py" -ForegroundColor Gray
Write-Host ""
Write-Host "   n8nワークフローを作成:" -ForegroundColor Cyan
Write-Host "     1. http://100.93.120.33:5678 にアクセス" -ForegroundColor Gray
Write-Host "     2. n8n_workflow_template.json をインポート" -ForegroundColor Gray
Write-Host "     3. ワークフローを有効化" -ForegroundColor Gray
Write-Host ""

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "起動完了" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""


















