# ManaOS統合システム起動スクリプト（PowerShell版）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ManaOS統合システム起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$services = @(
    @{
        Name = "統合APIサーバー"
        Script = "unified_api_server.py"
        Port = 9500
    },
    @{
        Name = "リアルタイムダッシュボード"
        Script = "realtime_dashboard.py"
        Port = 9600
    },
    @{
        Name = "マスターコントロールパネル"
        Script = "master_control.py"
        Port = 9700
    }
)

$processes = @()

foreach ($service in $services) {
    $scriptPath = Join-Path $PSScriptRoot $service.Script
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "[エラー] $($service.Script) が見つかりません" -ForegroundColor Red
        continue
    }
    
    # ポートチェック
    $portInUse = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "[スキップ] $($service.Name) は既に起動しています (ポート $($service.Port))" -ForegroundColor Yellow
        Write-Host "         URL: http://127.0.0.1:$($service.Port)" -ForegroundColor Gray
        continue
    }
    
    Write-Host "[起動中] $($service.Name)..." -ForegroundColor Green
    
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $scriptPath -PassThru -WindowStyle Hidden
        $processes += @{
            Name = $service.Name
            Process = $process
            Port = $service.Port
        }
        
        Start-Sleep -Seconds 3
        
        # ポートチェック
        $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
        if ($portCheck) {
            Write-Host "[成功] $($service.Name) が起動しました (ポート $($service.Port))" -ForegroundColor Green
            Write-Host "        URL: http://127.0.0.1:$($service.Port)" -ForegroundColor Cyan
        } else {
            Write-Host "[警告] $($service.Name) の起動を確認できませんでした" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[エラー] $($service.Name) の起動に失敗: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "起動完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "起動中のサービス:" -ForegroundColor Cyan
foreach ($proc in $processes) {
    Write-Host "  ✓ $($proc.Name): http://127.0.0.1:$($proc.Port)" -ForegroundColor Green
}

Write-Host ""
Write-Host "停止するには、各プロセスを終了するか、以下のコマンドを実行してください:" -ForegroundColor Yellow
Write-Host "  Get-Process python | Where-Object {$_.Path -like '*manaos_integrations*'} | Stop-Process" -ForegroundColor Gray
Write-Host ""


















