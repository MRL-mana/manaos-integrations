#!/usr/bin/env pwsh
<#
.SYNOPSIS
  X280 API Gateway 自動起動スクリプト
  PC起動時に x280_api_gateway.py を自動で起動する。

.DESCRIPTION
  - Python仮想環境を優先して使用（.venv or system python）
  - ポート 5120 でバインド
  - ログは C:\ManaOS\logs\x280_gateway.log に記録
  - タスクスケジューラー登録例が .NOTES に記載

.NOTES
  タスクスケジューラー登録（管理者権限で実行）:
    $script = "<THIS_FILE>"
    Register-ScheduledTask -TaskName "X280_API_Gateway" `
      -Action (New-ScheduledTaskAction -Execute "pwsh.exe" `
               -Argument "-NonInteractive -WindowStyle Hidden -File `"$script`"") `
      -Trigger (New-ScheduledTaskTrigger -AtStartup) `
      -Settings (New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)) `
      -RunLevel Highest -Force
#>

param(
    [string]$GatewayScript = "$PSScriptRoot\x280_api_gateway.py",
    [string]$LogDir         = "C:\ManaOS\logs",
    [int]   $Port           = 5120,
    [string]$Host           = "0.0.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"

# ログディレクトリ
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir "x280_gateway.log"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts][$Level] $Msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# Python 検索（仮想環境 → システム）
$pythonCandidates = @(
    "C:\ManaOS\.venv\Scripts\python.exe",
    "C:\Users\mana4\Desktop\.venv\Scripts\python.exe",
    "python.exe"
)
$PythonExe = $null
foreach ($p in $pythonCandidates) {
    if (Get-Command $p -ErrorAction SilentlyContinue) {
        $PythonExe = $p
        break
    }
}
if (-not $PythonExe) {
    Write-Log "Python が見つかりません" "ERROR"
    exit 1
}

Write-Log "Python: $PythonExe"
Write-Log "Gateway: $GatewayScript (port $Port)"

# 環境変数
$env:X280_API_PORT = "$Port"
$env:X280_API_HOST = $Host

# 既存プロセス確認（ポート占有）
$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
    Write-Log "Port $Port already in use (PID: $($existing[0].OwningProcess)) — skipping launch" "WARN"
    exit 0
}

Write-Log "Starting X280 API Gateway..."

# pip install チェック（fastapi, uvicorn）
$check = & $PythonExe -c "import fastapi, uvicorn; print('OK')" 2>&1
if ($check -ne "OK") {
    Write-Log "Installing dependencies..." "WARN"
    & $PythonExe -m pip install fastapi uvicorn --quiet
}

# 起動
& $PythonExe $GatewayScript 2>&1 | Tee-Object -FilePath $LogFile -Append
