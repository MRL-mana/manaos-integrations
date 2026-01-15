# ManaOS 新規サービス起動スクリプト

Write-Host "ManaOS 新規サービス起動中..." -ForegroundColor Cyan

$services = @(
    @{Name="Personality System"; Port=5123; Script="personality_system.py"},
    @{Name="Autonomy System"; Port=5124; Script="autonomy_system.py"},
    @{Name="Secretary System"; Port=5125; Script="secretary_system.py"},
    @{Name="Learning System API"; Port=5126; Script="learning_system_api.py"},
    @{Name="Metrics Collector"; Port=5127; Script="metrics_collector.py"},
    @{Name="Performance Dashboard"; Port=5128; Script="performance_dashboard.py"},
    @{Name="Intrinsic Motivation System"; Port=5130; Script="intrinsic_motivation.py"},
    @{Name="Intrinsic Motivation Metrics"; Port=5131; Script="intrinsic_motivation_metrics.py"},
    @{Name="Intrinsic Todo Generator"; Port=5132; Script="intrinsic_todo_generator.py"},
    @{Name="Reward Loop System"; Port=5133; Script="reward_loop.py"},
    @{Name="Intrinsic Todo Queue"; Port=5134; Script="intrinsic_todo_queue.py"}
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

foreach ($service in $services) {
    $scriptPath = Join-Path $scriptDir $service.Script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "⚠️  スクリプトが見つかりません: $($service.Script)" -ForegroundColor Yellow
        continue
    }
    
    # ポートが既に使用されているかチェック
    $portInUse = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "✅ $($service.Name): 既に起動中 (ポート $($service.Port))" -ForegroundColor Green
        continue
    }
    
    Write-Host "🚀 $($service.Name) 起動中... (ポート $($service.Port))" -ForegroundColor Cyan
    
    $logFile = Join-Path $logDir "$($service.Name.Replace(' ', '_')).log"
    $errorLogFile = Join-Path $logDir "$($service.Name.Replace(' ', '_'))_error.log"
    
    # バックグラウンドで起動（HiddenではなくNormalにしてエラーを確認可能に）
    Start-Process python -ArgumentList "`"$scriptPath`"" -WindowStyle Normal -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile
    
    Start-Sleep -Seconds 2
    
    # 起動確認
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "✅ $($service.Name): 起動成功" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $($service.Name): 起動確認できませんでした" -ForegroundColor Yellow
    }
}

Write-Host "`n新規サービス起動処理が完了しました。" -ForegroundColor Cyan

