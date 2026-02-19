# ManaOS 全サービス起動スクリプト
# すべてのサービスを一括起動

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     ManaOS 全サービス一括起動                                    ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

# 全サービス定義
$allServices = @(
    # コアサービス
    @{Name="Intent Router"; Port=5100; Script="intent_router.py"},
    @{Name="Task Planner"; Port=5101; Script="task_planner.py"},
    @{Name="Task Critic"; Port=5102; Script="task_critic.py"},
    @{Name="RAG Memory"; Port=5103; Script="rag_memory_enhanced.py"},
    @{Name="Task Queue"; Port=5104; Script="task_queue_system.py"},
    @{Name="UI Operations"; Port=5110; Script="ui_operations_api.py"},
    @{Name="Unified Orchestrator"; Port=5106; Script="unified_orchestrator.py"},
    @{Name="Executor Enhanced"; Port=5107; Script="task_executor_enhanced.py"},
    @{Name="Portal Integration"; Port=5108; Script="portal_integration_api.py"},
    @{Name="Content Generation"; Port=5109; Script="content_generation_loop.py"},
    @{Name="LLM Optimization"; Port=5110; Script="llm_optimization.py"},
    @{Name="System Status API"; Port=5112; Script="system_status_api.py"},
    
    # 拡張サービス
    @{Name="Personality System"; Port=5123; Script="personality_system.py"},
    @{Name="Autonomy System"; Port=5124; Script="autonomy_system.py"},
    @{Name="Secretary System"; Port=5125; Script="secretary_system.py"},
    @{Name="Learning System API"; Port=5126; Script="learning_system_api.py"},
    @{Name="Metrics Collector"; Port=5127; Script="metrics_collector.py"},
    @{Name="Performance Dashboard"; Port=5128; Script="performance_dashboard.py"},
    
    # 統合APIサーバー
    @{Name="Unified API Server"; Port=9500; Script="unified_api_server.py"}
)

Write-Host "[1] サービス起動チェック..." -ForegroundColor Yellow
Write-Host ""

$started = 0
$skipped = 0
$failed = 0

foreach ($service in $allServices) {
    $scriptPath = Join-Path $scriptDir $service.Script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "⚠️  $($service.Name): スクリプトが見つかりません ($($service.Script))" -ForegroundColor Yellow
        $failed++
        continue
    }
    
    # ポートが既に使用されているかチェック
    $portInUse = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "✅ $($service.Name): 既に起動中 (ポート $($service.Port))" -ForegroundColor Green
        $skipped++
        continue
    }
    
    Write-Host "🚀 $($service.Name) 起動中... (ポート $($service.Port))" -ForegroundColor Cyan
    
    $logFile = Join-Path $logDir "$($service.Name.Replace(' ', '_')).log"
    $errorLogFile = Join-Path $logDir "$($service.Name.Replace(' ', '_'))_error.log"
    
    # バックグラウンドで起動
    Start-Process python -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile
    
    Start-Sleep -Seconds 2
    
    # 起動確認
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "✅ $($service.Name): 起動成功" -ForegroundColor Green
        $started++
    } else {
        Write-Host "⚠️  $($service.Name): 起動確認できませんでした（ログを確認してください）" -ForegroundColor Yellow
        $failed++
    }
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║     起動処理完了                                                  ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 サマリー:" -ForegroundColor Yellow
Write-Host "   起動: $started サービス" -ForegroundColor Green
Write-Host "   既存: $skipped サービス" -ForegroundColor Cyan
Write-Host "   失敗: $failed サービス" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "📋 ログファイル: $logDir" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 状態確認: python check_service_status.py" -ForegroundColor Cyan
Write-Host ""
