param(
    [switch]$SkipDataGen,
    [switch]$DryRun,
    [switch]$ForceRestart,
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
$stdoutLog    = Join-Path $logDir "layer2_lora_v117_train_${timestamp}.stdout.log"
$stderrLog    = Join-Path $logDir "layer2_lora_v117_train_${timestamp}.stderr.log"
$launchLog    = Join-Path $logDir "layer2_lora_v117_train_${timestamp}.launch.log"
$monitorScript = Join-Path $root "monitor_v117_ckpt_then_quick_eval.ps1"

$pythonExe = (& py.exe -3.10 -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe -or -not (Test-Path $pythonExe)) { throw "python -3.10 not found" }

$baseModel      = "D:\castle_ex_training\castle_ex_v1_1"
$initLoraFrom   = "D:\castle_ex_training\lora_castle_ex_layer2_prod"   # v1.1.6 prod adapter
$outputDir      = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch"
$trainJsonl     = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_7_train.jsonl"
$evalJsonl      = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl"

# ── 1) データ生成（必要なら） ─────────────────────────────────────────────────
if (-not $SkipDataGen -or -not (Test-Path $trainJsonl)) {
    Write-Host "[step1] Generating v1.1.7 patch + train data..."
    & py.exe -3.10 castle_ex/generate_layer2_lora_data_v1_1_7.py
    if ($LASTEXITCODE -ne 0) { throw "data generation failed" }
}

# ── 2) 必須パス検証 ────────────────────────────────────────────────────────────
foreach ($p in @($baseModel, $initLoraFrom, $trainJsonl, $evalJsonl)) {
    if (-not (Test-Path $p)) { throw "required path not found: $p" }
}

# ── 3) 既存プロセス確認 ────────────────────────────────────────────────────────
$alreadyRunning = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*train_castle_ex_lora.py*" -and $_.CommandLine -like "*v1_1_7*" }

if ($alreadyRunning) {
    Write-Host "[INFO] v1.1.7 training already running."
    $alreadyRunning | Select-Object ProcessId, CommandLine | Format-Table -AutoSize
    if (-not $ForceRestart) { Write-Host "[INFO] Use -ForceRestart to stop and relaunch."; exit 0 }
    $pids = @($alreadyRunning | Select-Object -ExpandProperty ProcessId)
    if ($DryRun) { Write-Host "[DRY-RUN] would stop PIDs: $($pids -join ', ')"; exit 0 }
    foreach ($pid in $pids) { Stop-Process -Id $pid -Force -EA Stop; Write-Host "[INFO] stopped pid=$pid" }
    Start-Sleep -Seconds 2
}

# ── 4) 環境変数設定 ────────────────────────────────────────────────────────────
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE                 = "1"
# NOTE: expandable_segments:True は Blackwell (SM120/RTX5080) 非対応 → OOM の原因
# max_split_size_mb:512 はすべての GPU で動作し、断片化によるOOMを抑制する
$env:PYTORCH_CUDA_ALLOC_CONF      = "max_split_size_mb:512"
$env:PYTHONUNBUFFERED             = "1"
if ($env:TRANSFORMERS_CACHE) { $env:HF_HOME = $env:TRANSFORMERS_CACHE }

# ── 5) 学習引数 ────────────────────────────────────────────────────────────────
$trainArgs = @(
    "-u",
    "castle_ex\train_castle_ex_lora.py",
    "--base-model",                    $baseModel,
    "--init-lora-from",               $initLoraFrom,   # ← prod adapter から重み注入
    "--train-data",                    $trainJsonl,
    "--eval-data",                     $evalJsonl,
    "--output-dir",                    $outputDir,
    "--lora-r",                        "16",
    "--lora-alpha",                    "32",
    "--lora-dropout",                  "0.05",
    "--target-modules",                "q_proj,k_proj,v_proj,o_proj",
    "--max-length",                    "$MaxLength",
    "--batch-size",                    "$BatchSize",
    "--gradient-accumulation-steps",   "$GradientAccumulationSteps",
    "--learning-rate",                 "2e-4",
    "--max-steps",                     "$MaxSteps",
    "--save-steps",                    "$SaveSteps",
    "--eval-steps",                    "$EvalSteps",
    "--fp16"
)

@(
    "[v1.1.7] START patch LoRA training",
    "BASE_MODEL=$baseModel",
    "INIT_LORA_FROM=$initLoraFrom",
    "OUT_DIR=$outputDir",
    "TRAIN_JSONL=$trainJsonl",
    "EVAL_JSONL=$evalJsonl",
    "MAX_STEPS=$MaxSteps",
    "SAVE_STEPS=$SaveSteps",
    "LR=2e-4",
    "NOTE=init from prod adapter (v1.1.6), attribute_val_fix + part_whole_neg",
    "PYTHON_EXE=$pythonExe"
) | Out-File -FilePath $launchLog -Encoding utf8

if ($DryRun) {
    Write-Host "[DRY-RUN] launch: $pythonExe $($trainArgs -join ' ')"
    Write-Host "[DRY-RUN] launch log: $launchLog"
    exit 0
}

# ── 6) バックグラウンド起動 ────────────────────────────────────────────────────
$proc = Start-Process -FilePath $pythonExe -ArgumentList $trainArgs `
    -WorkingDirectory $root `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError  $stderrLog `
    -PassThru

Write-Host "[OK] launched v1.1.7 patch training"
Write-Host "  pid    : $($proc.Id)"
Write-Host "  stdout : $stdoutLog"
Write-Host "  stderr : $stderrLog"
Write-Host "  launch : $launchLog"

if (-not $NoMonitor) {
    if (Test-Path $monitorScript) {
        $mon = Start-Process -FilePath "powershell" `
            -ArgumentList @("-ExecutionPolicy","Bypass","-File",$monitorScript,"-CheckpointStep","$MaxSteps","-PollSec","60") `
            -WorkingDirectory $root -PassThru
        Write-Host "[OK] launched monitor pid=$($mon.Id) checkpoint=$MaxSteps"
    } else {
        Write-Host "[WARN] monitor script not found: $monitorScript"
    }
}

exit 0
