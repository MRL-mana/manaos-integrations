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
        Name = "Intrinsic Score API"
        Script = "intrinsic_motivation.py"
        Port = 5130
        HealthUrl = "http://localhost:5130/api/score"
    },
    @{
        Name = "Todo Queue API"
        Script = "intrinsic_todo_queue.py"
        Port = 5134
        HealthUrl = "http://localhost:5134/api/metrics"
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

    Start-Sleep -Seconds 3

    # 起動確認
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
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
