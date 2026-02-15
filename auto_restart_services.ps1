# LLMルーティングシステム 自動再起動スクリプト
# サービスが停止した場合、自動的に再起動

Write-Host "=" * 60
Write-Host "LLMルーティングシステム 自動再起動"
Write-Host "=" * 60
Write-Host ""

$workDir = Get-Location
$checkInterval = 30  # 30秒ごとにチェック

function Check-AndRestart-Service {
    param(
        [string]$ServiceName,
        [string]$ProcessMatch,
        [string]$StartCommand,
        [string]$HealthCheckUrl
    )
    
    try {
        Invoke-RestMethod -Uri $HealthCheckUrl -Method GET -TimeoutSec 2 -ErrorAction Stop | Out-Null
        return $true
    } catch {
        Write-Host "   [警告] $ServiceName が応答しません。再起動します..." -ForegroundColor Yellow
        
        # 既存のプロセスを停止
        try {
            Get-CimInstance Win32_Process | Where-Object {
                ($_.CommandLine -like "*$ProcessMatch*") -and ($_.Name -match "^(python|py)(\\.exe)?$")
            } | ForEach-Object {
                try {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                } catch {
                }
            }
        } catch {
            # 取得できない環境向けのフォールバック
            Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        
        Start-Sleep -Seconds 2
        
        # 再起動
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; $StartCommand" -WindowStyle Minimized
        
        Write-Host "   [OK] $ServiceName を再起動しました" -ForegroundColor Green
        return $false
    }
}

Write-Host "自動再起動モニターを開始します..." -ForegroundColor Cyan
Write-Host "チェック間隔: $checkInterval 秒" -ForegroundColor Gray
Write-Host "Ctrl+Cで終了" -ForegroundColor Gray
Write-Host ""

try {
    while ($true) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "[$timestamp] サービス状態をチェック中..." -ForegroundColor Yellow
        
        # Unified API
        $unifiedApiOk = Check-AndRestart-Service `
            -ServiceName "Unified API" `
            -ProcessMatch "unified_api_server.py" `
            -StartCommand "`$env:PYTHONIOENCODING='utf-8'; `$env:PORT='9510'; py -3.10 unified_api_server.py" `
            -HealthCheckUrl "http://127.0.0.1:9510/health"

        # LLM routing MCP (health only)
        $llmRoutingOk = Check-AndRestart-Service `
            -ServiceName "LLM Routing MCP" `
            -ProcessMatch "llm_routing_mcp_server" `
            -StartCommand "`$env:PYTHONIOENCODING='utf-8'; `$env:MANAOS_LOG_TO_STDERR='1'; python -m llm_routing_mcp_server" `
            -HealthCheckUrl "http://127.0.0.1:5111/health"
        
        if ($llmRoutingOk -and $unifiedApiOk) {
            Write-Host "   [OK] すべてのサービスが正常です" -ForegroundColor Green
        }
        
        Write-Host ""
        Start-Sleep -Seconds $checkInterval
    }
} catch {
    Write-Host ""
    Write-Host "監視を終了します..." -ForegroundColor Yellow
}



















