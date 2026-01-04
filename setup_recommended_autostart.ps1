# 標準構成（推奨）自動起動設定スクリプト
# 管理者権限で実行してください

$ErrorActionPreference = "Stop"

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ このスクリプトは管理者権限で実行する必要があります" -ForegroundColor Red
    Write-Host "PowerShellを「管理者として実行」してください" -ForegroundColor Yellow
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "=" * 60
Write-Host " 標準構成（推奨）自動起動設定" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

# 1. manaOS統合APIサーバーの確認
Write-Host "[1] manaOS統合APIサーバーの確認..." -ForegroundColor Yellow
$apiTask = Get-ScheduledTask -TaskName "manaOS-API-Server" -ErrorAction SilentlyContinue
if ($apiTask) {
    Write-Host "  ✅ 自動起動設定済み" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  自動起動未設定" -ForegroundColor Yellow
    Write-Host "  設定しますか？ (y/n)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -eq "y") {
        Write-Host "  manaOS統合APIサーバーの自動起動を設定中..." -ForegroundColor Gray
        & (Join-Path $scriptDir "setup_windows_autostart.ps1")
    }
}
Write-Host ""

# 2. n8nサービスの確認
Write-Host "[2] n8nワークフローエンジンの確認..." -ForegroundColor Yellow
$n8nService = Get-Service -Name "n8n" -ErrorAction SilentlyContinue
if ($n8nService) {
    Write-Host "  ✅ Windowsサービスとして登録済み" -ForegroundColor Green
    Write-Host "  状態: $($n8nService.Status)" -ForegroundColor Gray
    
    # 自動起動が有効か確認
    $wmiService = Get-WmiObject Win32_Service -Filter "Name='n8n'" -ErrorAction SilentlyContinue
    if ($wmiService -and $wmiService.StartMode -eq "Auto") {
        Write-Host "  ✅ 自動起動有効" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  自動起動が無効です" -ForegroundColor Yellow
        Write-Host "  自動起動を有効化しますか？ (y/n)" -ForegroundColor Yellow
        $answer = Read-Host
        if ($answer -eq "y") {
            Set-Service -Name "n8n" -StartupType Automatic
            Write-Host "  ✅ 自動起動を有効化しました" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ⚠️  Windowsサービス未登録" -ForegroundColor Yellow
    Write-Host "  n8nがインストールされているか確認中..." -ForegroundColor Gray
    
    $n8nPath = Get-Command n8n -ErrorAction SilentlyContinue
    if ($n8nPath) {
        Write-Host "  ✅ n8nが見つかりました: $($n8nPath.Source)" -ForegroundColor Green
        Write-Host "  Windowsサービスとして登録しますか？ (y/n)" -ForegroundColor Yellow
        $answer = Read-Host
        if ($answer -eq "y") {
            Write-Host "  n8nサービスをインストール中..." -ForegroundColor Gray
            & (Join-Path $scriptDir "install_n8n_service_simple.ps1")
        }
    } else {
        Write-Host "  ❌ n8nがインストールされていません" -ForegroundColor Red
        Write-Host "  先に n8n をインストールしてください:" -ForegroundColor Yellow
        Write-Host "    npm install -g n8n" -ForegroundColor Gray
    }
}
Write-Host ""

# 3. 設定サマリー
Write-Host "=" * 60
Write-Host " 設定サマリー" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

$apiTask = Get-ScheduledTask -TaskName "manaOS-API-Server" -ErrorAction SilentlyContinue
$n8nService = Get-Service -Name "n8n" -ErrorAction SilentlyContinue

Write-Host "サービス一覧:" -ForegroundColor Cyan
Write-Host ""

if ($apiTask) {
    Write-Host "  ✅ manaOS統合APIサーバー (ポート9500)" -ForegroundColor Green
    Write-Host "     自動起動: 有効" -ForegroundColor Gray
} else {
    Write-Host "  ❌ manaOS統合APIサーバー (ポート9500)" -ForegroundColor Red
    Write-Host "     自動起動: 未設定" -ForegroundColor Gray
}

if ($n8nService) {
    $wmiService = Get-WmiObject Win32_Service -Filter "Name='n8n'" -ErrorAction SilentlyContinue
    $autoStart = if ($wmiService -and $wmiService.StartMode -eq "Auto") { "有効" } else { "無効" }
    Write-Host "  ✅ n8nワークフローエンジン (ポート5679)" -ForegroundColor Green
    Write-Host "     自動起動: $autoStart" -ForegroundColor Gray
    Write-Host "     状態: $($n8nService.Status)" -ForegroundColor Gray
} else {
    Write-Host "  ❌ n8nワークフローエンジン (ポート5679)" -ForegroundColor Red
    Write-Host "     自動起動: 未設定" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 60
Write-Host " 次のステップ" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""
Write-Host "1. PCを再起動して動作確認" -ForegroundColor White
Write-Host "2. 各サービスの状態を確認:" -ForegroundColor White
Write-Host "   - manaOS: python check_server_status.py" -ForegroundColor Gray
Write-Host "   - n8n: Get-Service n8n" -ForegroundColor Gray
Write-Host ""
Write-Host "詳細は SETUP_RECOMMENDED_AUTOSTART.md を参照してください" -ForegroundColor Gray
Write-Host ""

