<#
.SYNOPSIS
  ManaOS: Docker Desktop + WSL integration 自動復旧スクリプト
.DESCRIPTION
  "WSL integration with distro unexpectedly stopped" 再発防止。
  - Docker Desktop 起動済み確認
  - WSL distro proxy 稼働確認
  - 問題があれば wsl --shutdown → Docker Desktop 再起動
.PARAMETER MaxWaitSec
  Docker エンジンの起動待ちタイムアウト（秒、デフォルト 60）
.PARAMETER WebhookUrl
  通知先 Slack Webhook URL（省略時は通知なし）
#>
param(
    [int]$MaxWaitSec = 60,
    [string]$WebhookUrl = ""
)

$ErrorActionPreference = "Stop"
$logDir = "$PSScriptRoot\..\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$logFile = Join-Path $logDir "docker_wsl_recovery_$(Get-Date -Format 'yyyyMMdd').log"
$dockerBin = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$dockerExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content $logFile $line -Encoding UTF8
}

function Notify($msg) {
    if ($WebhookUrl) {
        try {
            $body = @{ text = "Docker復旧: $msg" } | ConvertTo-Json
            Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType "application/json" | Out-Null
        } catch { Log "Slack通知失敗: $_" }
    }
}

Log "=== Docker WSL recovery check start ==="

# --- Step 1: WSL 状態確認 ---
$wslList = wsl -l -v 2>&1 | Out-String
Log "WSL状態: $($wslList.Trim())"
$ubuntuRunning = $wslList -match "Ubuntu-22.04\s+Running"
$ddRunning     = $wslList -match "docker-desktop\s+Running"

# --- Step 2: docker daemon 到達確認 ---
$dockerOk = $false
if (Test-Path $dockerBin) {
    try {
        $out = & $dockerBin version --format "{{.Server.Version}}" 2>&1
        if ($out -match '^\d+\.\d+') { $dockerOk = $true; Log "Docker engine OK: $out" }
        else { Log "Docker engine 応答なし: $out" }
    } catch { Log "Docker CLI エラー: $_" }
} else {
    Log "docker.exe 見つからず: $dockerBin"
}

# --- Step 3: 問題なければ終了 ---
if ($dockerOk -and $ubuntuRunning -and $ddRunning) {
    Log "すべて正常。復旧不要。"
    exit 0
}

# --- Step 4: 復旧処理 ---
Log "問題検出。復旧開始... (dockerOk=$dockerOk, ubuntu=$ubuntuRunning, dd=$ddRunning)"
Notify "Docker WSL integration 問題検出。自動復旧開始。"

# Docker Desktop 停止
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# WSL シャットダウン
Log "wsl --shutdown 実行中..."
wsl --shutdown
Start-Sleep -Seconds 5

# Docker Desktop 再起動
Log "Docker Desktop 再起動中..."
Start-Process $dockerExe
$elapsed = 0
while ($elapsed -lt $MaxWaitSec) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    try {
        $v = & $dockerBin version --format "{{.Server.Version}}" 2>&1
        if ($v -match '^\d+\.\d+') {
            Log "Docker engine 復旧確認: $v (${elapsed}秒後)"
            Notify "Docker WSL integration 復旧完了 ($v)。"
            exit 0
        }
    } catch {}
    Log "起動待ち... ${elapsed}秒"
}

Log "ERROR: ${MaxWaitSec}秒経過しても復旧できませんでした。"
Notify "Docker WSL integration 復旧失敗。手動確認が必要です。"
exit 1
