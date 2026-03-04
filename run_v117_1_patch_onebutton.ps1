#!/usr/bin/env pwsh
# run_v117_1_patch_onebutton.ps1
# NO-GO A回復用: v1.1.7.1 patch 学習（nogo_A_inject_and_retrain.ps1 実行後に使用）
# 使い方: powershell -ExecutionPolicy Bypass -File .\run_v117_1_patch_onebutton.ps1

param(
    [switch]$DryRun,
    [switch]$NoMonitor,
    [int]$MaxSteps = 300,
    [int]$SaveSteps = 100,
    [int]$EvalSteps = 150,
    [int]$MaxLength = 384,
    [int]$BatchSize = 1,
    [int]$GradientAccumulationSteps = 16
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$timestamp    = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutLog    = Join-Path $logDir "layer2_lora_v117_1_train_${timestamp}.stdout.log"
$stderrLog    = Join-Path $logDir "layer2_lora_v117_1_train_${timestamp}.stderr.log"
$launchLog    = Join-Path $logDir "layer2_lora_v117_1_train_${timestamp}.launch.log"
$monitorScript = Join-Path $root "monitor_v117_ckpt_then_quick_eval.ps1"

$pythonExe = (& py.exe -3.10 -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe -or -not (Test-Path $pythonExe)) { throw "python -3.10 not found" }

# v1.1.7.1 固有パス
$baseModel    = "D:\castle_ex_training\castle_ex_v1_1"
$outputDir    = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_1_patch"
$trainJsonl   = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_7_1_train.jsonl"
$evalJsonl    = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl"

# init-lora: v1.1.7 checkpoint-300 を起点（なければ root）
$v117outDir    = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch"
$v117ck300     = Join-Path $v117outDir "checkpoint-300"
$initLoraFrom  = if (Test-Path $v117ck300) { $v117ck300 } else { $v117outDir }
Write-Host "[init-lora] from: $initLoraFrom"

# 必須パス確認
foreach ($p in @($baseModel, $trainJsonl, $evalJsonl)) {
    if (-not (Test-Path $p)) { throw "required path not found: $p" }
}

# 出力ディレクトリ作成
if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir -Force | Out-Null }

# ── launch log ────────────────────────────────────────
@(
    "v1.1.7.1 patch training"
    "started: $(Get-Date -Format 's')"
    "base: $baseModel"
    "init_lora: $initLoraFrom"
    "output: $outputDir"
    "train: $trainJsonl"
    "lines: $((Get-Content $trainJsonl | Measure-Object -Line).Lines)"
    "MaxSteps=$MaxSteps GradAccum=$GradientAccumulationSteps"
) | Out-File -FilePath $launchLog -Encoding utf8

if ($DryRun) {
    Write-Host "[DRY-RUN] launch log: $launchLog"
    Get-Content $launchLog
    exit 0
}

# ── 環境変数 ────────────────────────────────────────────
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE                 = "1"
$env:PYTORCH_CUDA_ALLOC_CONF      = "expandable_segments:True"
$env:PYTHONUNBUFFERED             = "1"
if ($env:TRANSFORMERS_CACHE) { $env:HF_HOME = $env:TRANSFORMERS_CACHE }

# ── 学習引数（run_v117_onebutton.ps1 と同一構造）────────
$trainArgs = @(
    "-u",
    "castle_ex\train_castle_ex_lora.py",
    "--base-model",                   $baseModel,
    "--init-lora-from",               $initLoraFrom,
    "--train-data",                   $trainJsonl,
    "--eval-data",                    $evalJsonl,
    "--output-dir",                   $outputDir,
    "--lora-r",                       "16",
    "--lora-alpha",                   "32",
    "--lora-dropout",                 "0.05",
    "--target-modules",               "q_proj,k_proj,v_proj,o_proj",
    "--max-length",                   "$MaxLength",
    "--batch-size",                   "$BatchSize",
    "--gradient-accumulation-steps",  "$GradientAccumulationSteps",
    "--learning-rate",                "2e-4",
    "--max-steps",                    "$MaxSteps",
    "--save-steps",                   "$SaveSteps",
    "--eval-steps",                   "$EvalSteps",
    "--fp16"
)
$trainProc = Start-Process -FilePath $pythonExe -ArgumentList $trainArgs `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError  $stderrLog `
    -PassThru
Write-Host "[OK] launched v1.1.7.1 patch training"
Write-Host "  pid    : $($trainProc.Id)"
Write-Host "  stdout : $stdoutLog"
Write-Host "  stderr : $stderrLog"
Write-Host "  launch : $launchLog"

# ── モニター起動 ──────────────────────────────────────
if (-not $NoMonitor) {
    if (Test-Path $monitorScript) {
        $mon = Start-Process -FilePath "powershell" `
            -ArgumentList @("-ExecutionPolicy","Bypass","-File",$monitorScript,`
                            "-OutDir",$outputDir,"-CheckpointStep","$MaxSteps","-PollSec","60") `
            -WorkingDirectory $root -PassThru
        Write-Host "[OK] monitor PID=$($mon.Id) checkpoint=$MaxSteps"
    } else {
        Write-Host "[WARN] monitor script not found: $monitorScript"
    }
}
Write-Host "`n[READY] gate JSON → auto_gate_check_and_deploy_v117.ps1 で判定"
