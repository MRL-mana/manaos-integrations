# 母艦でn8nを起動するスクリプト（ポート5679）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n ローカル起動" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$n8nPort = if ($env:N8N_PORT) { $env:N8N_PORT } else { "5679" }
$n8nBaseUrl = if ($env:N8N_URL) { $env:N8N_URL.TrimEnd('/') } else { "http://127.0.0.1:$n8nPort" }

# ポート確認
$portInUse = Get-NetTCPConnection -LocalPort ([int]$n8nPort) -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[警告] ポート$n8nPort は既に使用されています" -ForegroundColor Yellow
    Write-Host "既存のn8nプロセスを終了します..." -ForegroundColor Yellow
    
    # 既存のn8nプロセスを終了
    $n8nProcesses = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { 
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
            $cmdLine -like "*n8n*"
        } catch {
            $false
        }
    }
    
    if ($n8nProcesses) {
        $n8nProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] 既存のn8nプロセスを終了しました" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host "[警告] n8nプロセスが見つかりませんでした" -ForegroundColor Yellow
        Write-Host "[NG] ポート$n8nPort が使用中のため、n8nを起動できません" -ForegroundColor Red
        exit 1
    }
}

# データディレクトリの確認
$n8nDataDir = "$env:USERPROFILE\.n8n"
if (-not (Test-Path $n8nDataDir)) {
    New-Item -ItemType Directory -Path $n8nDataDir | Out-Null
    Write-Host "[OK] データディレクトリを作成しました: $n8nDataDir" -ForegroundColor Green
}

# 環境変数を設定
$env:N8N_USER_FOLDER = $n8nDataDir
$env:N8N_PORT = $n8nPort
$env:N8N_LICENSE_KEY = "b01a8246-6a35-4221-917e-b5b25028a21b"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "n8n起動中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "ブラウザで以下のURLを開いてください:" -ForegroundColor Yellow
Write-Host "  $n8nBaseUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "停止するには Ctrl+C を押してください" -ForegroundColor Gray
Write-Host ""

# n8nを起動
n8n start --port $n8nPort















