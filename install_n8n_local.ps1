# 母艦（新PC）でn8nをインストール・起動するスクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n ローカルインストール" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Node.jsの確認
Write-Host "[1/5] Node.jsの確認..." -ForegroundColor Yellow
$nodeVersion = node --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NG] Node.jsがインストールされていません" -ForegroundColor Red
    Write-Host "Node.jsをインストールしてください: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
Write-Host ""

# n8nのインストール確認
Write-Host "[2/5] n8nのインストール確認..." -ForegroundColor Yellow
$n8nVersion = n8n --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[情報] n8nがインストールされていません。インストールします..." -ForegroundColor Yellow
    Write-Host ""
    
    # n8nをグローバルにインストール
    Write-Host "n8nをインストール中..." -ForegroundColor Cyan
    npm install -g n8n
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[NG] n8nのインストールに失敗しました" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] n8nをインストールしました" -ForegroundColor Green
} else {
    Write-Host "[OK] n8n: $n8nVersion" -ForegroundColor Green
}
Write-Host ""

# ポート5678の確認
Write-Host "[3/5] ポート5678の確認..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort 5678 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[警告] ポート5678は既に使用されています" -ForegroundColor Yellow
    Write-Host "別のポートを使用するか、既存のプロセスを終了してください" -ForegroundColor Yellow
    Write-Host ""
    $useDifferentPort = Read-Host "別のポートを使用しますか？ (y/n)"
    if ($useDifferentPort -eq "y") {
        $customPort = Read-Host "ポート番号を入力してください (デフォルト: 5679)"
        if ([string]::IsNullOrWhiteSpace($customPort)) {
            $customPort = "5679"
        }
        $env:N8N_PORT = $customPort
        Write-Host "[OK] ポート $customPort を使用します" -ForegroundColor Green
    } else {
        Write-Host "[NG] ポート5678が使用中のため、n8nを起動できません" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] ポート5678は使用可能です" -ForegroundColor Green
}
Write-Host ""

# データディレクトリの作成
Write-Host "[4/5] データディレクトリの作成..." -ForegroundColor Yellow
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
    Write-Host "[OK] データディレクトリを作成しました: $n8nDataDir" -ForegroundColor Green
} else {
    Write-Host "[OK] データディレクトリは既に存在します: $n8nDataDir" -ForegroundColor Green
}
Write-Host ""

# n8nの起動
Write-Host "[5/5] n8nを起動します..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n起動中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ブラウザで以下のURLを開いてください:" -ForegroundColor Yellow
if ($env:N8N_PORT) {
    Write-Host "  http://127.0.0.1:$env:N8N_PORT" -ForegroundColor Cyan
} else {
    Write-Host "  http://127.0.0.1:5678" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "停止するには Ctrl+C を押してください" -ForegroundColor Gray
Write-Host ""

# 環境変数を設定
$env:N8N_USER_FOLDER = $n8nDataDir

# n8nを起動
if ($env:N8N_PORT) {
    n8n start --port $env:N8N_PORT
} else {
    n8n start
}















