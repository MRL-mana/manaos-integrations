# n8nをWindowsサービスとしてインストールするスクリプト
# 管理者権限で実行が必要

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n Windowsサービス インストール" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[NG] このスクリプトは管理者権限で実行する必要があります" -ForegroundColor Red
    Write-Host "PowerShellを「管理者として実行」してから再度実行してください" -ForegroundColor Yellow
    exit 1
}

# n8nがインストールされているか確認
$n8nPath = Get-Command n8n -ErrorAction SilentlyContinue
if (-not $n8nPath) {
    Write-Host "[NG] n8nがインストールされていません" -ForegroundColor Red
    Write-Host "先に npm install -g n8n を実行してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] n8nが見つかりました: $($n8nPath.Source)" -ForegroundColor Green
Write-Host ""

# データディレクトリの確認
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
    Write-Host "[OK] データディレクトリを作成しました: $n8nDataDir" -ForegroundColor Green
}

# NSSM (Non-Sucking Service Manager) の確認・インストール
$nssmPath = "$env:ProgramFiles\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Write-Host "[情報] NSSMをインストールします..." -ForegroundColor Yellow
    Write-Host "NSSMはWindowsサービスを簡単に作成するツールです" -ForegroundColor Gray
    Write-Host ""
    
    # NSSMのダウンロードURL
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmExtract = "$env:TEMP\nssm"
    
    try {
        Write-Host "NSSMをダウンロード中..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip -UseBasicParsing
        
        Write-Host "NSSMを展開中..." -ForegroundColor Yellow
        Expand-Archive -Path $nssmZip -DestinationPath $nssmExtract -Force
        
        # 64bit版を使用
        $nssmExe = Get-ChildItem -Path $nssmExtract -Recurse -Filter "nssm.exe" | Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
        
        if ($nssmExe) {
            # Program Filesにコピー
            $nssmDir = "$env:ProgramFiles\nssm"
            New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
            Copy-Item $nssmExe.FullName -Destination $nssmPath -Force
            Write-Host "[OK] NSSMをインストールしました: $nssmPath" -ForegroundColor Green
        } else {
            throw "NSSMの実行ファイルが見つかりません"
        }
    } catch {
        Write-Host "[NG] NSSMのインストールに失敗しました: $_" -ForegroundColor Red
        Write-Host "手動でインストールしてください: https://nssm.cc/download" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[OK] NSSMが見つかりました: $nssmPath" -ForegroundColor Green
Write-Host ""

# 既存のサービスを確認
$serviceName = "n8n"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "[警告] 既存のn8nサービスが見つかりました" -ForegroundColor Yellow
    Write-Host "既存のサービスを削除して再インストールしますか？ (y/n)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -eq "y") {
        Write-Host "既存のサービスを停止中..." -ForegroundColor Yellow
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        
        Write-Host "既存のサービスを削除中..." -ForegroundColor Yellow
        & $nssmPath remove $serviceName confirm
        Start-Sleep -Seconds 2
    } else {
        Write-Host "[NG] インストールをキャンセルしました" -ForegroundColor Red
        exit 1
    }
}

# Node.jsのパスを取得
$nodePath = (Get-Command node).Source
$nodeDir = Split-Path $nodePath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8nサービスをインストール中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# サービスをインストール
Write-Host "サービス名: $serviceName" -ForegroundColor White
Write-Host "実行パス: $nodePath" -ForegroundColor White
Write-Host "引数: n8n start --port 5679" -ForegroundColor White
Write-Host "作業ディレクトリ: $n8nDataDir" -ForegroundColor White
Write-Host ""

# NSSMでサービスをインストール
& $nssmPath install $serviceName $nodePath "n8n start --port 5679"

# サービスの設定
& $nssmPath set $serviceName AppDirectory $n8nDataDir
& $nssmPath set $serviceName DisplayName "n8n Workflow Automation"
& $nssmPath set $serviceName Description "n8n workflow automation server on port 5679"
& $nssmPath set $serviceName Start SERVICE_AUTO_START

# 環境変数を設定
& $nssmPath set $serviceName AppEnvironmentExtra "N8N_USER_FOLDER=$n8nDataDir" "N8N_PORT=5679"

# ログ設定
$logDir = "$n8nDataDir\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
& $nssmPath set $serviceName AppStdout "$logDir\service.log"
& $nssmPath set $serviceName AppStderr "$logDir\service-error.log"

Write-Host ""
Write-Host "[OK] n8nサービスをインストールしました" -ForegroundColor Green
Write-Host ""

# サービスを開始
Write-Host "サービスを開始中..." -ForegroundColor Yellow
Start-Service -Name $serviceName
Start-Sleep -Seconds 3

# サービス状態を確認
$service = Get-Service -Name $serviceName
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "サービス状態" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "サービス名: $($service.Name)" -ForegroundColor White
Write-Host "表示名: $($service.DisplayName)" -ForegroundColor White
$statusColor = if ($service.Status -eq "Running") { "Green" } else { "Red" }
Write-Host "状態: $($service.Status)" -ForegroundColor $statusColor
Write-Host "起動タイプ: $((Get-WmiObject Win32_Service -Filter "Name='$serviceName'").StartMode)" -ForegroundColor White
Write-Host ""

if ($service.Status -eq "Running") {
    $n8nBaseUrl = if ($env:N8N_URL) {
        $env:N8N_URL.TrimEnd('/')
    } else {
        "http://127.0.0.1:5679"
    }
    Write-Host "[OK] n8nサービスが正常に起動しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "次のステップ" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "1. ブラウザで $n8nBaseUrl を開いてください" -ForegroundColor White
    Write-Host "2. サービス管理:" -ForegroundColor White
    Write-Host "   - 開始: Start-Service n8n" -ForegroundColor Gray
    Write-Host "   - 停止: Stop-Service n8n" -ForegroundColor Gray
    Write-Host "   - 再起動: Restart-Service n8n" -ForegroundColor Gray
    Write-Host "   - 状態確認: Get-Service n8n" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[警告] サービスが起動していません" -ForegroundColor Yellow
    Write-Host "ログを確認してください: $logDir\service-error.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "手動で開始: Start-Service n8n" -ForegroundColor Gray
}

