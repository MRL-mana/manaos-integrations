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
$fsEnv  = @{ PORT = "8089"; FILE_SECRETARY_PORT = "8089" }
$results["file-secretary"] = Start-WindowsService "file-secretary" $fsPath $fsEnv "" 8089

# ── step-deep-research (PORT 5120) ──
$sdrPath = "$ROOT\step_deep_research\run_server.py"
$results["step-deep-research"] = Start-WindowsService "step-deep-research" $sdrPath @{} "$ROOT" 5120

# ── ops-dashboard (PORT 9640) ──
$opsDashPath = "C:\Users\mana4\Desktop\ops-dashboard\backend\app.py"
$results["ops-dashboard"]  = Start-WindowsService "ops-dashboard" $opsDashPath @{} "C:\Users\mana4\Desktop\ops-dashboard\backend" 9640

# 3) ヘルスチェック実行
Write-Host ""
Write-Host "[3/4] Windows サービス ヘルスチェック..." -ForegroundColor Yellow

$healthTargets = @(
    @{ name = "file-secretary";      url = "http://127.0.0.1:8089/health" },
    @{ name = "step-deep-research";  url = "http://127.0.0.1:5120/health" },
    @{ name = "ops-dashboard";       url = "http://127.0.0.1:9640/health" }
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
