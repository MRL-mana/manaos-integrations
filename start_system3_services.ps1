# System 3 API Services Startup Script
# 必要なAPIサービスを起動

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System 3 API Services Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

# System 3に必要なサービス
$services = @(
    @{
        Name      = "Intrinsic Score API"
        Script    = "intrinsic_motivation.py"
        Port      = 5130
        HealthUrl = "http://127.0.0.1:5130/api/score"
    },
    @{
        Name      = "Todo Queue API"
        Script    = "intrinsic_todo_queue.py"
        Port      = 5134
        HealthUrl = "http://127.0.0.1:5134/api/metrics"
    },
    @{
        Name      = "Learning System API"
        Script    = "learning_system_api.py"
        Port      = 5126
        HealthUrl = "http://127.0.0.1:5126/health"
    },
    @{
        Name      = "RAG Memory API"
        Script    = "rag_memory_enhanced.py"
        Port      = 5103
        HealthUrl = "http://127.0.0.1:5103/health"
    }
)

foreach ($service in $services) {
    $scriptPath = Join-Path $scriptDir $service.Script

    if (-not (Test-Path $scriptPath)) {
        Write-Host "WARNING: Script not found: $($service.Script)" -ForegroundColor Red
        continue
    }

    # ポート確認
    $portInUse = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "[SKIP] $($service.Name): Already running (Port $($service.Port))" -ForegroundColor Yellow
        continue
    }

    Write-Host "[START] $($service.Name)..." -ForegroundColor Cyan

    $logFile = Join-Path $logDir "$($service.Name.Replace(' ', '_')).log"
    $errorLogFile = Join-Path $logDir "$($service.Name.Replace(' ', '_'))_error.log"

    # バックグラウンドで起動
    Start-Process python -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile

    $waitSec = if ($service.Port -in 5126, 5103) { 8 } else { 3 }
    Start-Sleep -Seconds $waitSec

    # 起動確認（Learning/RAG は追加リトライ）
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if (-not $portCheck -and $service.Port -in 5126, 5103) {
        Start-Sleep -Seconds 4
        $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    }
    if ($portCheck) {
        Write-Host "  OK: $($service.Name) started (Port $($service.Port))" -ForegroundColor Green

        # Health check
        try {
            $response = Invoke-RestMethod -Uri $service.HealthUrl -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
            if ($response) {
                Write-Host "  Health: OK" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Health: Checking..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  WARNING: $($service.Name) may not have started" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Startup Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Yellow
foreach ($service in $services) {
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "  - $($service.Name): RUNNING (Port $($service.Port))" -ForegroundColor Green
    } else {
        Write-Host "  - $($service.Name): STOPPED" -ForegroundColor Red
    }
}
Write-Host ""
