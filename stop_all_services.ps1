# ManaOS 全サービス停止スクリプト
# ポートベースとスクリプトベースの両方で停止

Write-Host "🛑 ManaOS 全サービス停止中..." -ForegroundColor Yellow

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
    @{Name="SSOT Generator"; Port=0; Script="ssot_generator.py"},
    @{Name="SSOT API"; Port=5120; Script="ssot_api.py"},
    @{Name="Unified API Server"; Port=9500; Script="unified_api_server.py"}
)

$stoppedCount = 0
$stoppedPids = @()

foreach ($service in $services) {
    $found = $false
    
    # ポートベースで停止（ポートが指定されている場合）
    if ($service.Port -ne 0) {
        $connections = netstat -ano | Select-String ":$($service.Port)\s+.*LISTENING"
        
        if ($connections) {
            foreach ($conn in $connections) {
                $pid = ($conn -split '\s+')[-1]
                if ($pid -and $pid -match '^\d+$' -and $stoppedPids -notcontains $pid) {
                    try {
                        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                        if ($proc) {
                            Write-Host "🛑 $($service.Name) 停止中 (Port: $($service.Port), PID: $pid)..." -ForegroundColor Yellow
                            Stop-Process -Id $pid -Force -ErrorAction Stop
                            $stoppedPids += $pid
                            $stoppedCount++
                            $found = $true
                            Write-Host "✅ $($service.Name) 停止完了 (PID: $pid)" -ForegroundColor Green
                        }
                    } catch {
                        Write-Host "⚠️  $($service.Name) 停止失敗 (PID: $pid): $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }
        }
    }
    
    # スクリプトベースで停止（ポートベースで見つからなかった場合）
    if (-not $found) {
        $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -and $cmdLine -like "*$($service.Script)*" -and $stoppedPids -notcontains $_.Id
        }
        
        foreach ($proc in $processes) {
            Write-Host "🛑 $($service.Name) 停止中 (PID: $($proc.Id))..." -ForegroundColor Yellow
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                $stoppedPids += $proc.Id
                $stoppedCount++
                Write-Host "✅ $($service.Name) 停止完了 (PID: $($proc.Id))" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  $($service.Name) 停止失敗 (PID: $($proc.Id)): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}

# プロセス情報ファイルのクリーンアップ
$processInfoFile = Join-Path $PSScriptRoot "process_info.json"
if (Test-Path $processInfoFile) {
    Write-Host "`nプロセス情報ファイルをクリーンアップ中..." -ForegroundColor Cyan
    Remove-Item $processInfoFile -Force -ErrorAction SilentlyContinue
    Write-Host "✅ プロセス情報ファイルを削除しました" -ForegroundColor Green
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "📊 停止完了: $stoppedCount プロセス" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

