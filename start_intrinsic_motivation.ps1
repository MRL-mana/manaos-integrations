# Intrinsic Motivation System 起動スクリプト

Write-Host "Intrinsic Motivation System 起動中..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "intrinsic_motivation.py"
$port = 5130

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ スクリプトが見つかりません: intrinsic_motivation.py" -ForegroundColor Red
    exit 1
}

# ポートが既に使用されているかチェック
$portInUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "✅ Intrinsic Motivation System: 既に起動中 (ポート $port)" -ForegroundColor Green
    exit 0
}

Write-Host "🚀 Intrinsic Motivation System 起動中... (ポート $port)" -ForegroundColor Cyan

$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "intrinsic_motivation.log"
$errorLogFile = Join-Path $logDir "intrinsic_motivation_error.log"

# 標準出力と標準エラーを分離して記録
Start-Process python -ArgumentList "`"$scriptPath`" $port" -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile

Start-Sleep -Seconds 3

# 起動確認
$portCheck = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "✅ Intrinsic Motivation System: 起動成功" -ForegroundColor Green
    Write-Host "   URL: http://127.0.0.1:$port" -ForegroundColor Gray
    Write-Host "   ログ: $logFile" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Intrinsic Motivation System: 起動確認できませんでした" -ForegroundColor Yellow
    Write-Host "   エラーログを確認してください: $errorLogFile" -ForegroundColor Yellow
}
