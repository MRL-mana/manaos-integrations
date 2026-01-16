# Redisコンテナを起動するスクリプト（必要に応じて）

Write-Host "Redisコンテナの状態を確認します..." -ForegroundColor Cyan

# Docker Desktopの起動確認
$dockerRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerRunning) {
    Write-Host "⚠️  Docker Desktopが起動していません" -ForegroundColor Yellow
    Write-Host "   Docker Desktopを起動してから再度実行してください" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ Docker Desktopは起動中です" -ForegroundColor Green

# Docker Engineの起動待機（最大30秒）
Write-Host "Docker Engineの起動を待機中..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
$dockerReady = $false

while ($waited -lt $maxWait) {
    try {
        $result = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            break
        }
    } catch {
        # エラーは無視
    }
    Start-Sleep -Seconds 2
    $waited += 2
    Write-Host "  ... ($waited 秒経過)" -ForegroundColor Gray
}

if (-not $dockerReady) {
    Write-Host "❌ Docker Engineが起動しませんでした（30秒経過）" -ForegroundColor Red
    Write-Host "   Docker Desktopが完全に起動するまで待ってから再度実行してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker Engineは起動中です" -ForegroundColor Green

# Redisコンテナの状態確認
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$redisStatus = docker-compose -f docker-compose.always-ready-llm.yml ps redis 2>&1
if ($redisStatus -match "Up|running") {
    Write-Host "✅ Redisコンテナは既に起動中です" -ForegroundColor Green
    exit 0
}

Write-Host "Redisコンテナを起動します..." -ForegroundColor Yellow
docker-compose -f docker-compose.always-ready-llm.yml up -d redis

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Redisコンテナを起動しました" -ForegroundColor Green
    Write-Host "   接続確認: redis-cli ping" -ForegroundColor Gray
} else {
    Write-Host "❌ Redisコンテナの起動に失敗しました" -ForegroundColor Red
    exit 1
}
