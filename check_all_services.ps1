# ManaOS 全サービス状態確認スクリプト

Write-Host "🔍 ManaOS 全サービス状態確認中..." -ForegroundColor Cyan
Write-Host "=" * 70

$services = @(
    @{Name="Intent Router"; Port=5100; Script="intent_router.py"},
    @{Name="Task Planner"; Port=5101; Script="task_planner.py"},
    @{Name="Task Critic"; Port=5102; Script="task_critic.py"},
    @{Name="RAG記憶進化"; Port=5103; Script="rag_memory_enhanced.py"},
    @{Name="汎用タスクキュー"; Port=5104; Script="task_queue_system.py"},
    @{Name="UI操作機能"; Port=5110; Script="ui_operations_api.py"},
    @{Name="統合オーケストレーター"; Port=5106; Script="unified_orchestrator.py"},
    @{Name="Executor拡張"; Port=5107; Script="task_executor_enhanced.py"},
    @{Name="Portal統合"; Port=5108; Script="portal_integration_api.py"},
    @{Name="成果物自動生成"; Port=5109; Script="content_generation_loop.py"},
    @{Name="LLM最適化"; Port=5110; Script="llm_optimization.py"}
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$results = @()

foreach ($service in $services) {
    $portCheck = Test-NetConnection -ComputerName 127.0.0.1 -Port $service.Port -WarningAction SilentlyContinue -InformationLevel Quiet
    
    $healthStatus = "Unknown"
    if ($portCheck) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$($service.Port)/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            $healthStatus = "Healthy ($($response.StatusCode))"
        } catch {
            $healthStatus = "Port Open but No Response"
        }
    } else {
        $healthStatus = "Not Running"
    }
    
    # プロセス確認
    $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -and $cmdLine -like "*$($service.Script)*"
    }
    
    $processInfo = if ($processes) {
        $proc = $processes[0]
        "PID: $($proc.Id)"
    } else {
        "No Process"
    }
    
    $results += [PSCustomObject]@{
        Name = $service.Name
        Port = $service.Port
        Status = $healthStatus
        Process = $processInfo
    }
}

$results | Format-Table -AutoSize

$runningCount = ($results | Where-Object { $_.Status -like "Healthy*" }).Count
$totalCount = $services.Count

Write-Host "`n📊 サマリー: $runningCount / $totalCount サービスが動作中" -ForegroundColor $(if ($runningCount -eq $totalCount) { "Green" } else { "Yellow" })

if ($runningCount -lt $totalCount) {
    Write-Host "`n💡 全サービスを起動: .\start_all_services.ps1" -ForegroundColor Cyan
}

