#!/usr/bin/env pwsh
# quick_check_ck100_v117.ps1
# checkpoint-100 で軽いevalを手動実行（早期シグナル取得）
# 使い方: powershell -ExecutionPolicy Bypass -File .\quick_check_ck100_v117.ps1

param(
    [int]   $CheckpointStep = 100,
    [string]$OutputDir      = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch",
    [string]$BaseModel      = "D:\castle_ex_training\castle_ex_v1_1",
    [string]$EvalData       = "castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl",
    [string]$ReportsDir     = "Reports"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }

$ckDir = Join-Path $OutputDir "checkpoint-$CheckpointStep"
if (-not (Test-Path $ckDir)) {
    Write-Log "checkpoint-$CheckpointStep まだ存在しません: $ckDir"
    Write-Log "存在するcheckpoints:"
    Get-ChildItem $OutputDir -Directory -Filter "checkpoint-*" | Select-Object Name
    exit 1
}

Write-Log "checkpoint-$CheckpointStep 確認 → eval開始"
$evalArgs = @(
    "-3.10", "-u",
    (Join-Path $root "scripts\run\run_layer2_quick_eval.py"),
    "--base-model",      $BaseModel,
    "--output-dir",      $OutputDir,
    "--checkpoint-step", $CheckpointStep,
    "--eval-data",       (Join-Path $root $EvalData),
    "--device-map",      "cuda:0",
    "--reports-dir",     (Join-Path $root $ReportsDir),
    "--max-new-tokens",  "64"
)

Write-Log "running: py $($evalArgs -join ' ')"
& py.exe @evalArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Log "[WARN] eval exited with code $exitCode"
    exit $exitCode
}

# 最新の eval JSON を取得して結果表示
$latest = Get-ChildItem (Join-Path $root $ReportsDir) -Filter "castle_ex_layer2_quick_eval_checkpoint-${CheckpointStep}_*.json" |
          Sort-Object LastWriteTime -Desc | Select-Object -First 1

if ($latest) {
    $evalJson = Get-Content $latest.FullName -Encoding UTF8 | ConvertFrom-Json
    $acc      = $evalJson.summary.acc
    Write-Log "=== checkpoint-$CheckpointStep 早期シグナル ========================"
    Write-Log "  acc = $acc (目標: >= 0.75)"
    Write-Log "  報告: $($latest.FullName)"
    if ($acc -ge 0.60) {
        Write-Log "  [OK] 0.60以上 → checkpoint-300 まで継続推奨"
    } elseif ($acc -ge 0.40) {
        Write-Log "  [WATCH] 0.40~0.59 → init-lora warm-start不発の可能性あり。300まで様子見"
    } else {
        Write-Log "  [ALERT] 0.40未満 → 学習が進んでいない可能性。stderr確認推奨"
        Write-Log "    cat logs\layer2_lora_v117_train_*.stderr.log | Select-Object -Last 20"
    }
    Write-Log "================================================================"
}
