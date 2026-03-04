#!/usr/bin/env pwsh
# ============================================================
# start_manaos_full.ps1  -  ManaOS ワンボタン起動オーケストレーター
# ============================================================
# 使い方:
#   .\start_manaos_full.ps1              # 通常起動
#   .\start_manaos_full.ps1 -Status      # 状態表示のみ
#   .\start_manaos_full.ps1 -Restart     # Docker 強制再起動
#   .\start_manaos_full.ps1 -StopAll     # 全停止
# ============================================================

param(
    [switch]$Status,
    [switch]$Restart,
    [switch]$StopAll,
    [switch]$NoBuild
)

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# ── カラーヘルパー ──────────────────────────────────────────
function Write-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║         ManaOS  Full  Orchestrator  v2.0         ║" -ForegroundColor Magenta
    Write-Host "║   Docker + Windows  Services  Unified  Launch    ║" -ForegroundColor Magenta
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""
}

function Write-Step($msg) {
    Write-Host "  ► $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-WARN($msg) {
    Write-Host "  ⚠ $msg" -ForegroundColor Yellow
}

function Write-ERR($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

# ── ヘルスチェック ──────────────────────────────────────────
function Test-Health($url, $timeoutSec = 5) {
    # url にパスが含まれる場合はそのまま、なければ /health を付加
    $checkUrl = if ($url -match "/-/|/healthz|/health$") { $url } else { "$url/health" }
    try {
        $res = Invoke-RestMethod -Uri $checkUrl -TimeoutSec $timeoutSec -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Show-ServiceHealth($name, $url) {
    $baseUrl = ($url -replace "/-/.*|/healthz.*|/health.*", "")
    if (Test-Health $url) {
        Write-OK "$name  $baseUrl"
    } else {
        Write-WARN "$name  $baseUrl  [unhealthy/offline]"
    }
}

# ── Docker 状態取得 ──────────────────────────────────────────
function Get-DockerStatus {
    try {
        $containers = docker ps --format "{{.Names}}\t{{.Status}}" 2>$null
        return $containers
    } catch {
        return $null
    }
}

function Show-DockerStatus {
    Write-Host "`n  [Docker コンテナ一覧]" -ForegroundColor DarkCyan
    $containers = Get-DockerStatus
    if ($null -eq $containers -or $containers.Count -eq 0) {
        Write-WARN "Docker 情報を取得できません（Desktop 再起動が必要かも）"
        return
    }
    foreach ($line in ($containers | Sort-Object)) {
        if ($line -match "Up.*healthy") {
            Write-Host "    $line" -ForegroundColor Green
        } elseif ($line -match "Restarting") {
            Write-Host "    $line" -ForegroundColor Red
        } elseif ($line -match "unhealthy") {
            Write-Host "    $line" -ForegroundColor Yellow
        } else {
            Write-Host "    $line" -ForegroundColor Gray
        }
    }
}

# ── v117 学習状態 ──────────────────────────────────────────
function Show-V117Status {
    $logPattern = "$ROOT\logs\monitor_v117_ck300_*.log"
    $logFile = Get-ChildItem $logPattern -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $logFile) {
        return
    }
    $lastLine = Get-Content $logFile.FullName | Select-Object -Last 1
    Write-Host "`n  [v117 学習状態]" -ForegroundColor DarkCyan
    if ($lastLine -match "waiting") {
        Write-WARN "  $lastLine"
    } elseif ($lastLine -match "eval|done|完了") {
        Write-OK  "  $lastLine"
    } else {
        Write-Host "    $lastLine" -ForegroundColor Gray
    }

    # stdout ログ最終行
    $stdoutLog = Get-ChildItem "$ROOT\logs\layer2_lora_v117_train_*.stdout.log" -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($stdoutLog) {
        $stdoutLast = Get-Content $stdoutLog.FullName | Select-Object -Last 3
        foreach ($l in $stdoutLast) {
            Write-Host "    $l" -ForegroundColor Gray
        }
    }
}

# ── Windows 側サービス起動 ──────────────────────────────────
function Start-WindowsServices {
    Write-Step "Windows 側サービス確認..."

    # Moltbot Gateway (8088)
    if (-not (Test-Health "http://127.0.0.1:8088")) {
        $moltbotScript = "$ROOT\moltbot_gateway\start_gateway.ps1"
        if (Test-Path $moltbotScript) {
            Write-Step "Moltbot Gateway 起動..."
            Start-Process pwsh -ArgumentList "-NonInteractive -File `"$moltbotScript`"" -WindowStyle Hidden
            Start-Sleep -Seconds 3
        }
    } else {
        Write-OK "Moltbot Gateway (8088) → 稼働中"
    }

    # Unified API の Windows 直接起動チェック（Docker で稼働中なら不要）
    if (Test-Health "http://127.0.0.1:9502") {
        Write-OK "Unified API (9502) → 稼働中"
    } else {
        Write-WARN "Unified API (9502) → offline（Docker コンテナ確認要）"
    }
}

# ── Docker 起動 ──────────────────────────────────────────────
function Start-DockerServices($forceRestart = $false) {
    Write-Step "Docker Desktop 接続確認..."
    $dockerOk = $false
    try {
        docker info 2>$null | Out-Null
        $dockerOk = ($LASTEXITCODE -eq 0)
    } catch {}

    if (-not $dockerOk) {
        Write-WARN "Docker Desktop が応答しません。スキップします。"
        return
    }
    Write-OK "Docker Desktop 接続 OK"

    $composeArgs = @("compose", "up", "-d")
    if ($forceRestart) {
        $composeArgs += "--force-recreate"
        Write-Step "Docker コンテナ強制再起動..."
    } else {
        $composeArgs += "--no-recreate"
        Write-Step "Docker コンテナ起動（変更分のみ更新）..."
    }
    if ($NoBuild) {
        $composeArgs += "--no-build"
    }

    & docker @composeArgs 2>&1 | Where-Object { $_ -match "Started|Running|Error|Warn" } | ForEach-Object {
        if ($_ -match "Error") { Write-ERR $_ } elseif ($_ -match "Warn") { Write-WARN $_ } else { Write-Host "    $_" -ForegroundColor Gray }
    }
    Write-OK "docker compose up 完了"
}

# ── 全停止 ────────────────────────────────────────────────────
function Stop-AllServices {
    Write-Host "`n  [全サービス停止]" -ForegroundColor DarkRed
    try {
        docker compose down 2>&1 | Select-Object -Last 5
        Write-OK "Docker コンテナ停止"
    } catch {
        Write-WARN "Docker 停止エラー: $_"
    }
}

# ── ステータスダッシュボード ─────────────────────────────────
function Show-StatusDashboard {
    Write-Host "`n══════════════ ManaOS ステータスボード ══════════════" -ForegroundColor Magenta

    $endpoints = @(
        @{name="Unified API     9502"; url="http://127.0.0.1:9502"},
        @{name="MRL Memory      9507"; url="http://127.0.0.1:9507"},
        @{name="Learning Sys    9508"; url="http://127.0.0.1:9508"},
        @{name="Prometheus      9090"; url="http://127.0.0.1:9090/-/healthy"},
        @{name="cAdvisor        8080"; url="http://127.0.0.1:8080/healthz"},
        @{name="Monitoring      5005"; url="http://127.0.0.1:5005"},
        @{name="Secretary API   5003"; url="http://127.0.0.1:5003"},
        @{name="OpenWebUI       3001"; url="http://127.0.0.1:3001"},
        @{name="Gallery API     5559"; url="http://127.0.0.1:5559"},
        @{name="Moltbot Gw      8088"; url="http://127.0.0.1:8088"},
        @{name="n8n             5678"; url="http://127.0.0.1:5678/healthz"}
    )

    Write-Host "`n  [HTTP ヘルスチェック]" -ForegroundColor DarkCyan
    foreach ($ep in $endpoints) {
        Show-ServiceHealth $ep.name $ep.url
    }

    Show-DockerStatus
    Show-V117Status

    Write-Host "`n══════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
    Write-Host ""
}

# ════════════════════════════════════════════════════════════
# メイン
# ════════════════════════════════════════════════════════════
Write-Banner

if ($Status) {
    Show-StatusDashboard
    exit 0
}

if ($StopAll) {
    Stop-AllServices
    exit 0
}

Write-Host "  起動シーケンス開始..." -ForegroundColor DarkGray

# 1. Docker サービス起動
Start-DockerServices -forceRestart:$Restart.IsPresent

# 2. Windows 側サービス確認
Start-Sleep -Seconds 5
Start-WindowsServices

# 3. ヘルス待機（最大60秒）
Write-Step "ヘルスチェック待機（最大60秒）..."
$waited = 0
while ($waited -lt 60) {
    if (Test-Health "http://127.0.0.1:9502") {
        break
    }
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Host "    ${waited}s 経過..." -ForegroundColor DarkGray
}

# 4. ステータスダッシュボード表示
Show-StatusDashboard
