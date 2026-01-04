# ManaOS 全サービス起動スクリプト
# 実装した全23サービスを起動（Core 11 + Phase 1 2 + Phase 2 3 + Phase 3 3 + SSOT 2 + Unified API 1 + Service Monitor 1）

Write-Host "ManaOS 全サービス起動中..." -ForegroundColor Cyan

$services = @(
    @{Name="Intent Router"; Port=5100; Script="intent_router.py"},
    @{Name="Task Planner"; Port=5101; Script="task_planner.py"},
    @{Name="Task Critic"; Port=5102; Script="task_critic.py"},
    @{Name="RAG Memory"; Port=5103; Script="rag_memory_enhanced.py"},
    @{Name="Task Queue"; Port=5104; Script="task_queue_system.py"},
    @{Name="UI Operations"; Port=5105; Script="ui_operations_api.py"},
    @{Name="Unified Orchestrator"; Port=5106; Script="unified_orchestrator.py"},
    @{Name="Executor Enhanced"; Port=5107; Script="task_executor_enhanced.py"},
    @{Name="Portal Integration"; Port=5108; Script="portal_integration_api.py"},
    @{Name="Content Generation"; Port=5109; Script="content_generation_loop.py"},
    @{Name="LLM Optimization"; Port=5110; Script="llm_optimization.py"},
    @{Name="Service Monitor"; Port=5111; Script="service_monitor.py"},
    @{Name="System Status API"; Port=5112; Script="system_status_api.py"},
    @{Name="Crash Snapshot"; Port=5113; Script="crash_snapshot.py"},
    @{Name="Slack Integration"; Port=5114; Script="slack_integration.py"},
    @{Name="Web Voice Interface"; Port=5115; Script="web_voice_interface.py"},
    @{Name="Portal Voice Integration"; Port=5116; Script="portal_voice_integration.py"},
    @{Name="Revenue Tracker"; Port=5117; Script="revenue_tracker.py"},
    @{Name="Product Automation"; Port=5118; Script="product_automation.py"},
    @{Name="Payment Integration"; Port=5119; Script="payment_integration.py"},
    @{Name="SSOT Generator"; Port=0; Script="ssot_generator.py"},
    @{Name="SSOT API"; Port=5120; Script="ssot_api.py"},
    @{Name="Learning System API"; Port=5126; Script="learning_system_api.py"},
    @{Name="Metrics Collector"; Port=5127; Script="metrics_collector.py"},
    @{Name="Performance Dashboard"; Port=5128; Script="performance_dashboard.py"},
    @{Name="Personality System"; Port=5123; Script="personality_system.py"},
    @{Name="Autonomy System"; Port=5124; Script="autonomy_system.py"},
    @{Name="Secretary System"; Port=5125; Script="secretary_system.py"},
    @{Name="Unified API Server"; Port=9500; Script="unified_api_server.py"}
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$startedServices = @()

# 重複プロセスチェック・終了
Write-Host "`n重複プロセスチェック中..." -ForegroundColor Cyan
foreach ($service in $services) {
    if ($service.Port -eq 0) {
        continue
    }
    
    # ポートを使用しているプロセスを取得
    $connections = netstat -ano | Select-String ":$($service.Port)\s+.*LISTENING"
    
    if ($connections) {
        $pids = @()
        foreach ($conn in $connections) {
            $pid = ($conn -split '\s+')[-1]
            if ($pid -and $pid -match '^\d+$') {
                $pids += $pid
            }
        }
        
        $uniquePids = $pids | Sort-Object -Unique
        
        if ($uniquePids.Count -gt 1) {
            Write-Host "⚠️  $($service.Name): Port $($service.Port) で $($uniquePids.Count)個のプロセスを検出、重複を終了します..." -ForegroundColor Yellow
            
            # 最初のプロセスを残して、残りを終了
            $keepPid = $uniquePids[0]
            $killPids = $uniquePids[1..($uniquePids.Count-1)]
            
            foreach ($pid in $killPids) {
                try {
                    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($proc) {
                        $proc | Stop-Process -Force -ErrorAction SilentlyContinue
                        Write-Host "  ✅ PID $pid を終了しました" -ForegroundColor Green
                    }
                } catch {
                    # エラーは無視（既に終了している可能性）
                }
            }
            
            Start-Sleep -Seconds 1
        }
    }
}

Write-Host "`nサービス起動開始..." -ForegroundColor Cyan

foreach ($service in $services) {
    $scriptPath = Join-Path $scriptDir $service.Script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "⚠️  スクリプトが見つかりません: $($service.Script)" -ForegroundColor Yellow
        continue
    }
    
    # ポートが既に使用されているかチェック
    if ($service.Port -ne 0) {
        $portInUse = Test-NetConnection -ComputerName localhost -Port $service.Port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($portInUse) {
            Write-Host "⚠️  $($service.Name): Port $($service.Port) は既に使用されています。スキップします。" -ForegroundColor Yellow
            $startedServices += @{
                Name = $service.Name
                Port = $service.Port
                PID = 0
                Status = "AlreadyRunning"
            }
            continue
        }
    }
    
    Write-Host "$($service.Name) (Port: $($service.Port)) 起動中..." -ForegroundColor Green
    
    $logFile = Join-Path $logDir "$($service.Script -replace '\.py$', '.log')"
    
    # バックグラウンドで起動
    $errorLogFile = $logFile -replace '\.log$', '_error.log'
    $process = Start-Process -FilePath "python" -ArgumentList $scriptPath -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile
    
    Start-Sleep -Seconds 3
    
    # ポートが開いているか確認
    if ($service.Port -ne 0) {
        $portCheck = Test-NetConnection -ComputerName localhost -Port $service.Port -WarningAction SilentlyContinue -InformationLevel Quiet
    } else {
        $portCheck = $true  # ポート0の場合は常にTrue
    }
    
    $processId = if ($process) { $process.Id } else { 0 }
    
    if ($portCheck -or $service.Port -eq 0) {
        Write-Host "✅ $($service.Name) 起動完了 (PID: $processId)" -ForegroundColor Green
        $startedServices += @{
            Name = $service.Name
            Port = $service.Port
            PID = $processId
            Status = "Running"
        }
    } else {
        Write-Host "⚠️  $($service.Name) 起動確認できませんでした (PID: $processId)" -ForegroundColor Yellow
        $startedServices += @{
            Name = $service.Name
            Port = $service.Port
            PID = $processId
            Status = "Starting"
        }
    }
}

Write-Host "`n起動状況サマリー:" -ForegroundColor Cyan
Write-Host "=" * 60

foreach ($svc in $startedServices) {
    $statusColor = if ($svc.Status -eq "Running") { "Green" } else { "Yellow" }
    $pidStr = if ($svc.PID) { $svc.PID.ToString().PadLeft(6) } else { "N/A".PadLeft(6) }
    Write-Host "$($svc.Name.PadRight(25)) Port: $($svc.Port.ToString().PadLeft(5)) PID: $pidStr Status: $($svc.Status)" -ForegroundColor $statusColor
}

Write-Host "`nログファイル: $logDir" -ForegroundColor Cyan
Write-Host "サービス停止: .\stop_all_services.ps1" -ForegroundColor Cyan

