# ManaOS 重複プロセスチェック・終了スクリプト
# 同じポートを使用している重複プロセスを検出して終了

Write-Host "ManaOS 重複プロセスチェック中..." -ForegroundColor Cyan

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
    @{Name="System Status API"; Port=5112; Script="system_status_api.py"},
    @{Name="Crash Snapshot"; Port=5113; Script="crash_snapshot.py"},
    @{Name="Slack Integration"; Port=5114; Script="slack_integration.py"},
    @{Name="Web Voice Interface"; Port=5115; Script="web_voice_interface.py"},
    @{Name="Portal Voice Integration"; Port=5116; Script="portal_voice_integration.py"},
    @{Name="Revenue Tracker"; Port=5117; Script="revenue_tracker.py"},
    @{Name="Product Automation"; Port=5118; Script="product_automation.py"},
    @{Name="Payment Integration"; Port=5119; Script="payment_integration.py"},
    @{Name="SSOT API"; Port=5120; Script="ssot_api.py"},
    @{Name="LLM Routing MCP"; Port=5111; Script="llm_routing_mcp_server"},
    @{Name="Unified API Server"; Port=9510; Script="unified_api_server.py"}
)

$totalKilled = 0

foreach ($service in $services) {
    if ($service.Port -eq 0) {
        continue
    }
    
    Write-Host "`n$($service.Name) (Port: $($service.Port)) チェック中..." -ForegroundColor Yellow
    
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
        
        # 重複を除去
        $uniquePids = $pids | Sort-Object -Unique
        
        if ($uniquePids.Count -gt 1) {
            Write-Host "⚠️  重複プロセス検出: $($uniquePids.Count)個のプロセスがPort $($service.Port)を使用しています" -ForegroundColor Red
            
            # 最初のプロセスを残して、残りを終了
            $keepPid = $uniquePids[0]
            $killPids = $uniquePids[1..($uniquePids.Count-1)]
            
            Write-Host "  保持: PID $keepPid" -ForegroundColor Green
            
            foreach ($pid in $killPids) {
                try {
                    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                    if ($proc) {
                        $procName = $proc.ProcessName
                        $proc | Stop-Process -Force
                        Write-Host "  ✅ 終了: PID $pid ($procName)" -ForegroundColor Green
                        $totalKilled++
                    }
                } catch {
                    Write-Host "  ⚠️  終了失敗: PID $pid ($($_.Exception.Message))" -ForegroundColor Yellow
                }
            }
        } elseif ($uniquePids.Count -eq 1) {
            Write-Host "  ✅ 正常: 1プロセスのみ (PID: $($uniquePids[0]))" -ForegroundColor Green
        }
    } else {
        Write-Host "  ℹ️  ポート $($service.Port) は使用されていません" -ForegroundColor Gray
    }
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "重複プロセスチェック完了" -ForegroundColor Cyan
Write-Host "終了したプロセス数: $totalKilled" -ForegroundColor $(if ($totalKilled -gt 0) { "Yellow" } else { "Green" })
Write-Host "=" * 60 -ForegroundColor Cyan

