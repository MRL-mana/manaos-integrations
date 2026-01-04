# ManaOS統合システム 起動確認スクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ManaOS統合システム 起動確認" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. ComfyUI確認
Write-Host "[1] ComfyUI起動確認..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8188/system_stats" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "   [OK] ComfyUIは起動中です" -ForegroundColor Green
    } else {
        Write-Host "   [NG] ComfyUIが起動していません" -ForegroundColor Red
    }
} catch {
    Write-Host "   [NG] ComfyUIが起動していません" -ForegroundColor Red
    Write-Host "   起動: .\start_comfyui_local.ps1" -ForegroundColor Gray
}
Write-Host ""

# 2. 統合APIサーバー確認
Write-Host "[2] 統合APIサーバー起動確認..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:9500/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "   [OK] 統合APIサーバーは起動中です" -ForegroundColor Green
        $integrations = $response.integrations
        if ($integrations) {
            Write-Host "   統合システム:" -ForegroundColor Gray
            foreach ($key in $integrations.PSObject.Properties.Name) {
                $status = if ($integrations.$key) { "[OK]" } else { "[NG]" }
                Write-Host "     $status $key" -ForegroundColor $(if ($integrations.$key) { "Green" } else { "Red" })
            }
        }
    } else {
        Write-Host "   [NG] 統合APIサーバーが起動していません" -ForegroundColor Red
    }
} catch {
    Write-Host "   [NG] 統合APIサーバーが起動していません" -ForegroundColor Red
    Write-Host "   起動: python unified_api_server.py" -ForegroundColor Gray
}
Write-Host ""

# 3. Google Drive確認
Write-Host "[3] Google Drive認証確認..." -ForegroundColor Yellow
$credentialsPath = Join-Path $scriptDir "credentials.json"
$tokenPath = Join-Path $scriptDir "token.json"
if ((Test-Path $credentialsPath) -and (Test-Path $tokenPath)) {
    Write-Host "   [OK] Google Drive認証情報が設定されています" -ForegroundColor Green
} else {
    Write-Host "   [NG] Google Drive認証情報が不足しています" -ForegroundColor Red
}
Write-Host ""

# 4. n8n確認
Write-Host "[4] n8n起動確認..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://100.93.120.33:5678" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "   [OK] n8nは起動中です" -ForegroundColor Green
        Write-Host "   URL: http://100.93.120.33:5678" -ForegroundColor Gray
    } else {
        Write-Host "   [NG] n8nが起動していません" -ForegroundColor Red
    }
} catch {
    Write-Host "   [NG] n8nが起動していません（このはサーバー側）" -ForegroundColor Yellow
    Write-Host "   このはサーバー側でn8nを起動してください" -ForegroundColor Gray
}
Write-Host ""

# 5. n8n Webhook URL確認
Write-Host "[5] n8n Webhook URL確認..." -ForegroundColor Yellow
$n8nWebhookUrl = $env:N8N_WEBHOOK_URL
if ($n8nWebhookUrl) {
    Write-Host "   [OK] n8n Webhook URLが設定されています" -ForegroundColor Green
    Write-Host "   URL: $n8nWebhookUrl" -ForegroundColor Gray
} else {
    Write-Host "   [INFO] n8n Webhook URLが設定されていません" -ForegroundColor Yellow
    Write-Host "   設定: `$env:N8N_WEBHOOK_URL = 'http://100.93.120.33:5678/webhook/comfyui-generated'" -ForegroundColor Gray
}
Write-Host ""

# まとめ
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "確認完了" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# 次のアクション
Write-Host "次のアクション:" -ForegroundColor Yellow
Write-Host "  1. 統合APIサーバーを起動:" -ForegroundColor Cyan
Write-Host "     python unified_api_server.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. 完全統合テストを実行:" -ForegroundColor Cyan
Write-Host "     python complete_integration_test.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. n8nワークフローを作成:" -ForegroundColor Cyan
Write-Host "     n8n_ワークフローセットアップ.md を参照" -ForegroundColor Gray
Write-Host ""


















