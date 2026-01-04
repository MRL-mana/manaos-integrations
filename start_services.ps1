# ManaOS統合システム起動スクリプト（改善版）
# 各サービスを個別のウィンドウで起動

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ManaOS統合システム起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

$services = @(
    @{
        Name = "統合APIサーバー"
        Script = "unified_api_server.py"
        Port = 9500
    }
)

# 既存のプロセスをチェック
foreach ($service in $services) {
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portCheck) {
        $portNum = $service.Port
        Write-Host "[スキップ] $($service.Name) は既に起動しています (ポート $portNum)" -ForegroundColor Yellow
        Write-Host "         URL: http://localhost:$portNum" -ForegroundColor Gray
    } else {
        Write-Host "[起動中] $($service.Name)..." -ForegroundColor Green
        
        $scriptFullPath = Join-Path $scriptPath $service.Script
        Start-Process -FilePath "python" -ArgumentList "`"$scriptFullPath`"" -WindowStyle Normal
        
        Write-Host "[起動] $($service.Name) を新しいウィンドウで起動しました" -ForegroundColor Green
        Write-Host "        URL: http://localhost:$($service.Port)" -ForegroundColor Cyan
        Write-Host ""
        
        Start-Sleep -Seconds 3
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "起動完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "起動中のサービス:" -ForegroundColor Cyan
foreach ($service in $services) {
    $portCheck = Get-NetTCPConnection -LocalPort $service.Port -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "  ✓ $($service.Name): http://localhost:$($service.Port)" -ForegroundColor Green
    }
}
Write-Host ""
Write-Host "ブラウザで以下のURLにアクセスしてください:" -ForegroundColor Yellow
Write-Host "  http://localhost:9500/health" -ForegroundColor Cyan
Write-Host ""

