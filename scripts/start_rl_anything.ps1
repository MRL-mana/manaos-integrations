<#
.SYNOPSIS
  RLAnything 起動スクリプト — 環境変数セット + スモークテスト + ステータス表示
.DESCRIPTION
  ManaOS の RLAnything 自己進化フレームワークを有効化し、
  動作確認テストを実行して現在のステータスをダッシュボード表示する。
.EXAMPLE
  .\start_rl_anything.ps1              # 有効化 + テスト
  .\start_rl_anything.ps1 -TestOnly    # テストだけ
  .\start_rl_anything.ps1 -Dashboard   # ダッシュボードのみ
#>
[CmdletBinding()]
param(
    [switch]$TestOnly,
    [switch]$Dashboard,
    [switch]$Enable,
    [switch]$Disable
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot   # manaos_integrations/
if (-not (Test-Path "$root\rl_anything\orchestrator.py")) {
    $root = $PSScriptRoot
}

# ═════════════════════════════════════════════
# 環境変数の設定
# ═════════════════════════════════════════════
if ($Enable -or (-not $TestOnly -and -not $Dashboard -and -not $Disable)) {
    $env:RL_ANYTHING = "on"
    Write-Host "[RLAnything] Enabled (env:RL_ANYTHING=on)" -ForegroundColor Green
}
if ($Disable) {
    $env:RL_ANYTHING = "off"
    Write-Host "[RLAnything] Disabled (env:RL_ANYTHING=off)" -ForegroundColor Yellow
    return
}

# ═════════════════════════════════════════════
# テスト実行
# ═════════════════════════════════════════════
if (-not $Dashboard) {
    Write-Host ""
    Write-Host "=== RLAnything Smoke Test ===" -ForegroundColor Cyan
    Push-Location $root
    try {
        $result = & py -3.10 rl_anything/test_rl_anything.py 2>&1
        $exitCode = $LASTEXITCODE
        $result | ForEach-Object { Write-Host "  $_" }
        if ($exitCode -eq 0) {
            Write-Host "`n  [OK] All tests passed" -ForegroundColor Green
        } else {
            Write-Host "`n  [NG] Some tests failed (exit=$exitCode)" -ForegroundColor Red
        }
    } finally {
        Pop-Location
    }
    if ($TestOnly) { return }
}

# ═════════════════════════════════════════════
# ダッシュボード表示
# ═════════════════════════════════════════════
Write-Host ""
Write-Host "=== RLAnything Dashboard ===" -ForegroundColor Cyan

$dashScript = @"
import sys, json
sys.path.insert(0, r'$root')
from rl_anything.orchestrator import RLAnythingOrchestrator
rl = RLAnythingOrchestrator()
d = rl.get_dashboard()
print(json.dumps(d, ensure_ascii=False, indent=2))
"@

$dashJson = & py -3.10 -c $dashScript 2>&1
if ($LASTEXITCODE -eq 0) {
    $dash = $dashJson | ConvertFrom-Json
    Write-Host "  Cycle count    : $($dash.cycle_count)"
    Write-Host "  Difficulty     : $($dash.current_difficulty)"
    Write-Host "  Total tasks    : $($dash.observation.total)"
    Write-Host "  Success rate   : $($dash.observation.success_rate)"
    Write-Host "  Skills         : $($dash.evolution.skills_count)"
} else {
    Write-Host "  Dashboard error:" -ForegroundColor Yellow
    $dashJson | ForEach-Object { Write-Host "    $_" }
}

# ═════════════════════════════════════════════
# MEMORY.md チェック
# ═════════════════════════════════════════════
$memPath = Join-Path $root "MEMORY.md"
if (Test-Path $memPath) {
    $memSize = (Get-Item $memPath).Length
    Write-Host "  MEMORY.md      : $memSize bytes" -ForegroundColor Green
} else {
    Write-Host "  MEMORY.md      : not found" -ForegroundColor Yellow
}

# ═════════════════════════════════════════════
# ログディレクトリ
# ═════════════════════════════════════════════
$logDir = Join-Path $root "logs\rl_anything"
if (Test-Path $logDir) {
    $logFiles = Get-ChildItem $logDir -Filter "*.jsonl" -ErrorAction SilentlyContinue
    Write-Host "  Log files      : $($logFiles.Count)"
} else {
    Write-Host "  Log files      : (no logs yet)"
}

Write-Host ""
Write-Host "[RLAnything] Ready. Use env:RL_ANYTHING=on to enable in phase1_hooks." -ForegroundColor Green
