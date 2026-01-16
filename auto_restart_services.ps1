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
        [string]$ScriptPath,
        [string]$HealthCheckUrl
    )
    
    try {
        $response = Invoke-WebRequest -Uri $HealthCheckUrl -Method GET -TimeoutSec 2 -ErrorAction Stop
        return $true
    } catch {
        Write-Host "   [警告] $ServiceName が応答しません。再起動します..." -ForegroundColor Yellow
        
        # 既存のプロセスを停止
        Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -like "*$ScriptPath*"
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Start-Sleep -Seconds 2
        
        # 再起動
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; `$env:PYTHONIOENCODING='utf-8'; python $ScriptPath" -WindowStyle Minimized
        
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
        
        # LLMルーティングAPI
        $llmApiOk = Check-AndRestart-Service `
            -ServiceName "LLMルーティングAPI" `
            -ScriptPath "manaos_llm_routing_api.py" `
            -HealthCheckUrl "http://localhost:9501/api/llm/health"
        
        # 統合APIサーバー
        $unifiedApiOk = Check-AndRestart-Service `
            -ServiceName "統合APIサーバー" `
            -ScriptPath "unified_api_server.py" `
            -HealthCheckUrl "http://localhost:9500/health"
        
        if ($llmApiOk -and $unifiedApiOk) {
            Write-Host "   [OK] すべてのサービスが正常です" -ForegroundColor Green
        }
        
        Write-Host ""
        Start-Sleep -Seconds $checkInterval
    }
} catch {
    Write-Host ""
    Write-Host "監視を終了します..." -ForegroundColor Yellow
}



















