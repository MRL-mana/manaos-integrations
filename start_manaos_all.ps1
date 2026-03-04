#Requires -Version 5.1
<#
.SYNOPSIS
    ManaOS 全サービス起動スクリプト
.DESCRIPTION
    Windows 再起動後に ManaOS の全 Windows 直接起動サービスを自動起動します。
    Docker/WSL サービスは docker-compose が別途管理しています。
.EXAMPLE
    .\start_manaos_all.ps1
    .\start_manaos_all.ps1 -SkipHealthCheck
#>

param(
    [switch]$SkipHealthCheck,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ROOT = "C:\Users\mana4\Desktop\manaos_integrations"
$PYTHON = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"

# ── ヘルパー関数 ────────────────────────────────────────────────
function Write-Step([string]$msg) {
    Write-Host "  >> $msg" -ForegroundColor Cyan
}
function Write-OK([string]$msg) {
    Write-Host "  [OK] $msg" -ForegroundColor Green
}
function Write-WARN([string]$msg) {
    Write-Host " [WARN] $msg" -ForegroundColor Yellow
}
function Write-FAIL([string]$msg) {
    Write-Host " [FAIL] $msg" -ForegroundColor Red
}

function Test-PortListening([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return ($conn -ne $null)
}

function Wait-PortReady([int]$port, [int]$timeoutSec = 15) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-WindowsService([string]$name, [string]$scriptPath, [hashtable]$env = @{}, [string]$workDir = "", [int]$port = 0) {
    Write-Step "起動チェック: $name (PORT $port)"

    if ($port -gt 0 -and (Test-PortListening $port)) {
        Write-OK "$name は既に起動中 (port $port)"
        return $true
    }

    if (-not (Test-Path $scriptPath)) {
        Write-FAIL "$name: スクリプトが見つかりません: $scriptPath"
        return $false
    }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $PYTHON
    $psi.Arguments = "`"$scriptPath`""
    $psi.WorkingDirectory = if ($workDir) { $workDir } else { Split-Path $scriptPath }
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.UseShellExecute = $true

    # 環境変数をセット（UseShellExecute=trueでは直接セットできないので Start-Process -Environment を使う）
    if ($env.Count -gt 0) {
        $envArgs = $env.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
        $psi.UseShellExecute = $false
        foreach ($kv in $env.GetEnumerator()) {
            $psi.EnvironmentVariables[$kv.Key] = $kv.Value
        }
    }

    try {
        $proc = [System.Diagnostics.Process]::Start($psi)
        Write-Step "$name 起動中 (PID $($proc.Id))..."

        if ($port -gt 0) {
            $ready = Wait-PortReady $port 15
            if ($ready) {
                Write-OK "$name 起動完了 (port $port)"
                return $true
            } else {
                Write-WARN "$name: 15秒待機後もポート $port が開かない（バックグラウンドで起動継続中の可能性あり）"
                return $false
            }
        }
        return $true
    } catch {
        Write-FAIL "$name 起動失敗: $_"
        return $false
    }
}

function Invoke-HealthCheck([string]$url, [int]$timeoutSec = 5) {
    try {
        $resp = Invoke-RestMethod -Uri $url -TimeoutSec $timeoutSec -ErrorAction Stop
        return @{ ok = $true; body = $resp }
    } catch {
        return @{ ok = $false; body = "$_" }
    }
}

# ── メイン処理 ──────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "   ManaOS 全サービス起動スクリプト" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""

# 1) Docker Desktop が動いているか確認
Write-Host "[1/4] Docker Desktop チェック..." -ForegroundColor Yellow
$dockerProc = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProc) {
    Write-OK "Docker Desktop 稼働中"
} else {
    Write-WARN "Docker Desktop が起動していません。起動を試みます..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Normal
    Write-Step "Docker Desktop 起動待機（30秒）..."
    Start-Sleep 30
}

# 2) Windows 直接起動サービスを起動
Write-Host ""
Write-Host "[2/4] Windows 直接起動サービスを起動..." -ForegroundColor Yellow

$results = @{}

# ── file-secretary (PORT 8089) ──
$fsPath = "$ROOT\file_secretary\file_secretary_api.py"
$fsEnv  = @{ FILE_SECRETARY_PORT = "8089"; PORT = "8089" }
$results["file-secretary"] = Start-WindowsService "file-secretary" $fsPath $fsEnv "" 8089
$env:PORT = ""  # step-deep-research に PORT=8089 が継承されないようリセット

# ── step-deep-research (PORT 5120) ──
$sdrPath = "$ROOT\step_deep_research\run_server.py"
$results["step-deep-research"] = Start-WindowsService "step-deep-research" $sdrPath @{} "$ROOT" 5120

# ── personality-system (PORT 5123) ──
$psysPath = "$ROOT\scripts\misc\personality_system.py"
$results["personality-system"] = Start-WindowsService "personality-system" $psysPath @{ PERSONALITY_SYSTEM_PORT = "5123"; PORT = "5123" } "$ROOT" 5123

# ── autonomy-system (PORT 5124) ──
$asysPath = "$ROOT\scripts\misc\autonomy_system.py"
$results["autonomy-system"] = Start-WindowsService "autonomy-system" $asysPath @{ AUTONOMY_SYSTEM_PORT = "5124"; PORT = "5124" } "$ROOT" 5124

# ── secretary-system (PORT 5125) ──
$ssysPath = "$ROOT\scripts\misc\secretary_system.py"
$results["secretary-system"] = Start-WindowsService "secretary-system" $ssysPath @{ SECRETARY_SYSTEM_PORT = "5125"; PORT = "5125" } "$ROOT" 5125

# ── personality-thought-system (PORT 5126) ──
$ptsysPath = "$ROOT\scripts\misc\personality_thought_system.py"
$results["personality-thought-system"] = Start-WindowsService "personality-thought-system" $ptsysPath @{ PERSONALITY_THOUGHT_PORT = "5126"; PORT = "5126" } "$ROOT" 5126

# ── ops-dashboard (PORT 9640) ──
$opsDashPath = "C:\Users\mana4\Desktop\ops-dashboard\backend\app.py"
$results["ops-dashboard"]  = Start-WindowsService "ops-dashboard" $opsDashPath @{} "C:\Users\mana4\Desktop\ops-dashboard\backend" 9640

# ── unified-api-server / MCP API server (PORT 9502) ──
$uapiPath = "$ROOT\unified_api_server.py"
$results["unified-api-server"] = Start-WindowsService "unified-api-server" $uapiPath @{ PORT = "9502"; UNIFIED_API_PORT = "9502" } "$ROOT" 9502

# ── mrl-memory (PORT 5105) ──
$mrlPath = "$ROOT\mrl_memory_integration.py"
$results["mrl-memory"] = Start-WindowsService "mrl-memory" $mrlPath @{ PORT = "5105"; MRL_MEMORY_PORT = "5105" } "$ROOT" 5105

# 3) ヘルスチェック実行
Write-Host ""
Write-Host "[3/4] Windows サービス ヘルスチェック..." -ForegroundColor Yellow

$healthTargets = @(
    @{ name = "file-secretary";      url = "http://127.0.0.1:8089/health" },
    @{ name = "step-deep-research";  url = "http://127.0.0.1:5120/health" },
    @{ name = "personality-system";  url = "http://127.0.0.1:5123/health" },
    @{ name = "autonomy-system";     url = "http://127.0.0.1:5124/health" },
    @{ name = "secretary-system";    url = "http://127.0.0.1:5125/health" },
    @{ name = "personality-thought-system"; url = "http://127.0.0.1:5126/health" },
    @{ name = "ops-dashboard";       url = "http://127.0.0.1:9640/health" },
    @{ name = "unified-api-server";  url = "http://127.0.0.1:9502/health" },
    @{ name = "mrl-memory";          url = "http://127.0.0.1:5105/health" }
)

if (-not $SkipHealthCheck) {
    foreach ($svc in $healthTargets) {
        $hc = Invoke-HealthCheck $svc.url
        if ($hc.ok) {
            Write-OK "$($svc.name) /health → OK"
        } else {
            Write-WARN "$($svc.name) /health → $($hc.body)"
        }
    }
}

# 4) 全体ヘルスチェック（Python スクリプト）
Write-Host ""
Write-Host "[4/4] 全サービス ヘルスチェック..." -ForegroundColor Yellow
if (-not $SkipHealthCheck) {
    & $PYTHON "$ROOT\tools\health_check_all.py" --format=compact 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-WARN "一部サービスが offline です（要確認）"
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "   ManaOS 起動完了！" -ForegroundColor Green
Write-Host "   ヘルスチェック: python tools/health_check_all.py" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
