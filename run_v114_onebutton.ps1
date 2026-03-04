param(
    [switch]$SkipDataGen,
    [switch]$DryRun,
    [switch]$ForceRestart,
    [switch]$NoMonitor,
    [int]$MaxSteps = 4500,
    [int]$SaveSteps = 100,
    [int]$EvalSteps = 500,
    [int]$MaxLength = 384,
    [int]$BatchSize = 1,
    [int]$GradientAccumulationSteps = 16,
    [string]$ResumeFromCheckpoint = "auto"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdoutLog = Join-Path $logDir "layer2_lora_v114_train_${timestamp}.stdout.log"
$stderrLog = Join-Path $logDir "layer2_lora_v114_train_${timestamp}.stderr.log"
$launchLog = Join-Path $logDir "layer2_lora_v114_train_${timestamp}.launch.log"
$monitorScript = Join-Path $root "monitor_v114_ckpt1500_then_quick_eval.ps1"

$pythonExe = (& py.exe -3.10 -c "import sys; print(sys.executable)").Trim()
if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    throw "python executable not found for -3.10"
}

$baseModel = "D:\castle_ex_training\castle_ex_v1_1"
$outputDir = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_4_stylefix"
$trainJsonl = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_4_stylefix_train.jsonl"
$evalJsonl = Join-Path $root "castle_ex_dataset_layer2_lora_v1_1_4_stylefix_eval.jsonl"
$defaultResume = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3\checkpoint-3000"

if ($ResumeFromCheckpoint -eq "auto") {
    $resumePath = "auto"
}
elseif ([string]::IsNullOrWhiteSpace($ResumeFromCheckpoint)) {
    $resumePath = $defaultResume
}
else {
    $resumePath = $ResumeFromCheckpoint
}

if (-not (Test-Path $baseModel)) {
    throw "base model not found: $baseModel"
}

if (-not $SkipDataGen) {
    $generator = Join-Path $root "castle_ex\generate_layer2_lora_data_v114.py"
    if (Test-Path $generator) {
        Write-Host "[INFO] generating v1.1.4 stylefix dataset..."
        & py.exe -3.10 -u $generator
    }
    else {
        Write-Host "[WARN] data generator not found: $generator"
        Write-Host "[WARN] continue with existing JSONL files"
    }
}

if (-not (Test-Path $trainJsonl)) {
    throw "train jsonl not found: $trainJsonl"
}
if (-not (Test-Path $evalJsonl)) {
    throw "eval jsonl not found: $evalJsonl"
}

$alreadyRunning = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*train_castle_ex_lora.py*" -and $_.CommandLine -like "*v1_1_4_stylefix*" }

if ($alreadyRunning) {
    Write-Host "[INFO] v1.1.4 stylefix training already running."
    $alreadyRunning | Select-Object ProcessId, CommandLine | Format-Table -AutoSize

    if (-not $ForceRestart) {
        Write-Host "[INFO] Use -ForceRestart to stop current process and relaunch."
        exit 0
    }

    $pids = @($alreadyRunning | Select-Object -ExpandProperty ProcessId)
    if ($DryRun) {
        Write-Host "[DRY-RUN] would stop existing PID(s): $($pids -join ', ')"
        Write-Host "[DRY-RUN] then relaunch training with current arguments."
        exit 0
    }

    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "[INFO] stopped pid=$pid"
        }
        catch {
            throw "failed to stop existing training pid=${pid}: $($_.Exception.Message)"
        }
    }

    Start-Sleep -Seconds 2
}

$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE = "1"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"
$env:PYTHONUNBUFFERED = "1"

$args = @(
    "-u",
    "castle_ex\train_castle_ex_lora.py",
    "--base-model", $baseModel,
    "--train-data", $trainJsonl,
    "--eval-data", $evalJsonl,
    "--output-dir", $outputDir,
    "--lora-r", "16",
    "--lora-alpha", "32",
    "--lora-dropout", "0.05",
    "--target-modules", "q_proj,k_proj,v_proj,o_proj",
    "--max-length", "$MaxLength",
    "--batch-size", "$BatchSize",
    "--gradient-accumulation-steps", "$GradientAccumulationSteps",
    "--learning-rate", "2e-4",
    "--max-steps", "$MaxSteps",
    "--save-steps", "$SaveSteps",
    "--eval-steps", "$EvalSteps",
    "--fp16",
    "--resume-from-checkpoint", $resumePath
)

@(
    "[v1.1.4] START style-fix LoRA training",
    "BASE_MODEL=$baseModel",
    "RESUME_CHECKPOINT=$defaultResume",
    "OUT_DIR=$outputDir",
    "TRAIN_JSONL=$trainJsonl",
    "EVAL_JSONL=$evalJsonl",
    "MAX_STEPS=$MaxSteps",
    "MAX_LENGTH=$MaxLength",
    "BATCH_SIZE=$BatchSize",
    "GRAD_ACCUM=$GradientAccumulationSteps",
    "RESUME_ARG=$resumePath",
    "PYTHON_EXE=$pythonExe"
) | Out-File -FilePath $launchLog -Encoding utf8

if ($DryRun) {
    Write-Host "[DRY-RUN] launch command: $pythonExe $($args -join ' ')"
    Write-Host "[DRY-RUN] launch log: $launchLog"
    exit 0
}

$proc = Start-Process -FilePath $pythonExe -ArgumentList $args -WorkingDirectory $root -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

Write-Host "[OK] launched v1.1.4 style-fix training"
Write-Host "  pid: $($proc.Id)"
Write-Host "  stdout: $stdoutLog"
Write-Host "  stderr: $stderrLog"
Write-Host "  launch: $launchLog"

if (-not $NoMonitor) {
    if (Test-Path $monitorScript) {
        $mon = Start-Process -FilePath "powershell" -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $monitorScript, "-CheckpointStep", "$MaxSteps", "-PollSec", "120") -WorkingDirectory $root -PassThru
        Write-Host "[OK] launched monitor pid=$($mon.Id) script=$monitorScript checkpoint=$MaxSteps"
    }
    else {
        Write-Host "[WARN] monitor script not found: $monitorScript"
    }
}

exit 0
