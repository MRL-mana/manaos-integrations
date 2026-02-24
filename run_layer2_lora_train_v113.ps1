#!/usr/bin/env pwsh
# v1.1.3: Layer2 LoRA 学習ランナー（stdout/stderrをlogsへ退避して事故原因を追えるようにする）
param(
    [int]$MaxSteps = 3000,
    [int]$SaveSteps = 100,
    [int]$EvalSteps = 500,
    [string]$ResumeFromCheckpoint = "auto"
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutLog = Join-Path $logDir "layer2_lora_v113_train_$timestamp.stdout.log"
$stderrLog = Join-Path $logDir "layer2_lora_v113_train_$timestamp.stderr.log"
$pidFile  = Join-Path $logDir "layer2_lora_v113_train_$timestamp.pid.txt"

$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE = "1"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"
$env:PYTHONUNBUFFERED = "1"

$arguments = @(
    "-3.10", "-u",
    "castle_ex\\train_castle_ex_lora.py",
    "--base-model", "D:\\castle_ex_training\\castle_ex_v1_1",
    "--train-data", "castle_ex_dataset_layer2_lora_train_v1_1_3.jsonl",
    "--eval-data", "castle_ex_dataset_layer2_lora_eval_v1_1_3.jsonl",
    "--output-dir", "D:\\castle_ex_training\\lora_castle_ex_layer2_v1_1_3",
    "--lora-r", "16",
    "--lora-alpha", "32",
    "--lora-dropout", "0.05",
    "--target-modules", "q_proj,k_proj,v_proj,o_proj",
    "--max-length", "512",
    "--batch-size", "2",
    "--gradient-accumulation-steps", "8",
    "--learning-rate", "2e-4",
    "--max-steps", "$MaxSteps",
    "--save-steps", "$SaveSteps",
    "--eval-steps", "$EvalSteps",
    "--fp16"
)

if ($ResumeFromCheckpoint -and $ResumeFromCheckpoint.Trim().Length -gt 0) {
    $arguments += @("--resume-from-checkpoint", $ResumeFromCheckpoint)
}

Write-Host "[START] v1.1.3 training: max_steps=$MaxSteps save_steps=$SaveSteps eval_steps=$EvalSteps resume=$ResumeFromCheckpoint"
Write-Host "  stdout: $stdoutLog"
Write-Host "  stderr: $stderrLog"

$proc = Start-Process -FilePath "py.exe" -ArgumentList $arguments -WorkingDirectory $root -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

Set-Content -Path $pidFile -Value $proc.Id -Encoding utf8
Write-Host "[OK] launched pid=$($proc.Id) pidFile=$pidFile"
