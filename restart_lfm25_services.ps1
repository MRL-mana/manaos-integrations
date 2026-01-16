# LFM 2.5統合サービス再起動スクリプト
# Phase 1 + Phase 2で変更したサービスを再起動

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LFM 2.5統合サービス再起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 変更したサービス一覧
$services = @(
    @{Name="Intent Router"; Port=5100; Script="intent_router.py"},
    @{Name="Task Planner"; Port=5101; Script="task_planner.py"},
    @{Name="Content Generation"; Port=5109; Script="content_generation_loop.py"},
    @{Name="Unified API Server"; Port=9500; Script="unified_api_server.py"}
)

Write-Host "[1] 既存プロセスを確認・停止中..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $services) {
    Write-Host "  - $($service.Name) (Port: $($service.Port))" -ForegroundColor Cyan
    
    # ポートを使用しているプロセスを確認
    $portProcess = netstat -ano | Select-String ":$($service.Port)\s" | ForEach-Object {
        $_.ToString().Split()[-1]
    } | Select-Object -Unique
    
    if ($portProcess) {
        foreach ($pid in $portProcess) {
            try {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($proc) {
                    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $pid").CommandLine
                    if ($cmdLine -and $cmdLine -like "*$($service.Script)*") {
                        Write-Host "    PID $pid を停止中..." -ForegroundColor Yellow
                        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                        Start-Sleep -Seconds 1
                    }
                }
            } catch {
                # プロセスが見つからない場合はスキップ
            }
        }
    }
    
    # スクリプト名でプロセスを検索
    $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -and $cmdLine -like "*$($service.Script)*"
        } catch {
            $false
        }
    }
    
    if ($processes) {
        foreach ($proc in $processes) {
            Write-Host "    PID $($proc.Id) を停止中..." -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    
    Write-Host "    ✓ 停止完了" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2] サービスを起動中..." -ForegroundColor Yellow
Write-Host ""

# Intent Routerを起動
Write-Host "  - Intent Router起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "intent_router.py" -WindowStyle Minimized
Start-Sleep -Seconds 3

# Task Plannerを起動
Write-Host "  - Task Planner起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "task_planner.py" -WindowStyle Minimized
Start-Sleep -Seconds 3

# Content Generationを起動
Write-Host "  - Content Generation起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "content_generation_loop.py" -WindowStyle Minimized
Start-Sleep -Seconds 3

# Unified API Serverを起動
Write-Host "  - Unified API Server起動中..." -ForegroundColor Cyan
Start-Process python -ArgumentList "unified_api_server.py" -WindowStyle Minimized
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "[3] ヘルスチェック中..." -ForegroundColor Yellow
Write-Host ""

# ヘルスチェック
Start-Sleep -Seconds 5

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✓ $($service.Name): 起動成功 (HTTP $($response.StatusCode))" -ForegroundColor Green
    } catch {
        # ポートチェック
        $portCheck = Test-NetConnection -ComputerName localhost -Port $service.Port -WarningAction SilentlyContinue -InformationLevel Quiet
        if ($portCheck) {
            Write-Host "  ⚠ $($service.Name): ポートは開いていますが、ヘルスチェックに失敗しました" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ $($service.Name): 起動確認失敗（数秒待ってから再確認してください）" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "再起動完了" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "LFM 2.5統合状況:" -ForegroundColor Cyan
Write-Host "  ✓ Intent Router: LFM 2.5使用" -ForegroundColor Green
Write-Host "  ✓ Secretary Routines: LFM 2.5使用（Unified API経由）" -ForegroundColor Green
Write-Host "  ✓ Task Planner: 簡単な計画でLFM 2.5使用" -ForegroundColor Green
Write-Host "  ✓ Content Generation: 下書き生成でLFM 2.5使用" -ForegroundColor Green
Write-Host ""
Write-Host "効果確認方法:" -ForegroundColor Cyan
Write-Host "  python test_lfm25_integration.py" -ForegroundColor Yellow
Write-Host ""
