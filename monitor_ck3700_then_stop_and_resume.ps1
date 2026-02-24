param(
    [int]$IntervalSeconds = 120,
    [int]$CheckpointStep = 3700,
    [int]$MaxSteps = 4000,
    [int]$GracefulWaitSeconds = 900,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$root = "C:\Users\mana4\Desktop\manaos_integrations"
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$outputDir = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_2"
$ckPath = Join-Path $outputDir ("checkpoint-{0}" -f $CheckpointStep)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$monitorLog = Join-Path $logDir "monitor_ck${CheckpointStep}_$timestamp.log"
$stdoutPath = Join-Path $logDir "layer2_lora_resume_after_ck${CheckpointStep}_$timestamp.stdout.log"
$stderrPath = Join-Path $logDir "layer2_lora_resume_after_ck${CheckpointStep}_$timestamp.stderr.log"

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] start monitor: ckPath=$ckPath interval=$IntervalSeconds" | Add-Content $monitorLog -Encoding utf8

function Get-TrainingProcess {
    # python.exeでtrain_castle_ex_lora.pyを実行しているプロセスを取得
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*train_castle_ex_lora.py*" }
}

while ($true) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $ckExists = Test-Path $ckPath
    $trainProc = Get-TrainingProcess
    $trainAlive = $null -ne $trainProc

    "[$now] train_alive=$trainAlive ck_exists=$ckExists" | Add-Content $monitorLog -Encoding utf8

    if ($ckExists) {
        "[$now] [TRIGGER_DETECTED] checkpoint-$CheckpointStep exists" | Add-Content $monitorLog -Encoding utf8
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}

# checkpointが出たので停止フェーズ
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$trainProc = Get-TrainingProcess
if ($null -eq $trainProc) {
    "[$now] training process not found; nothing to stop" | Add-Content $monitorLog -Encoding utf8
} else {
    $trainPid = [int]$trainProc.ProcessId
    "[$now] requesting stop: pid=$trainPid" | Add-Content $monitorLog -Encoding utf8

    # 可能ならSTOPファイルでの停止を依頼（新スクリプトで起動されたプロセスなら有効）
    try {
        $stopFile = Join-Path $outputDir "STOP_TRAINING"
        New-Item -ItemType File -Path $stopFile -Force | Out-Null
        "[$now] STOP file created: $stopFile" | Add-Content $monitorLog -Encoding utf8
    } catch {
        "[$now] STOP file create failed: $($_.Exception.Message)" | Add-Content $monitorLog -Encoding utf8
    }

    # 一定時間待っても止まらなければ、checkpointがある前提で強制停止
    $deadline = (Get-Date).AddSeconds($GracefulWaitSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 10
        $still = Get-Process -Id $trainPid -ErrorAction SilentlyContinue
        if ($null -eq $still) {
            break
        }
    }

    $still = Get-Process -Id $trainPid -ErrorAction SilentlyContinue
    if ($null -ne $still) {
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$now] graceful stop timeout; force stop pid=$trainPid" | Add-Content $monitorLog -Encoding utf8
        Stop-Process -Id $trainPid -Force
    } else {
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$now] training stopped gracefully" | Add-Content $monitorLog -Encoding utf8
    }
}

if ($NoRestart) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$now] NoRestart specified; done" | Add-Content $monitorLog -Encoding utf8
    exit 0
}

# 再開前にSTOPファイルが残っていると、新しい学習プロセスが即停止してしまうため削除する
try {
    $stopFile = Join-Path $outputDir "STOP_TRAINING"
    if (Test-Path $stopFile) {
        Remove-Item -Force $stopFile
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$now] removed STOP file before restart: $stopFile" | Add-Content $monitorLog -Encoding utf8
    }
} catch {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$now] failed to remove STOP file before restart: $($_.Exception.Message)" | Add-Content $monitorLog -Encoding utf8
}

# 再開フェーズ（checkpointからautoで再開）
Set-Location $root
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE = "1"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"
$env:PYTHONUNBUFFERED = "1"

$args = @(
    "-3.10",
    "-u",
    "castle_ex\train_castle_ex_lora.py",
    "--base-model", "D:\castle_ex_training\castle_ex_v1_1",
    "--train-data", "castle_ex_dataset_layer2_lora_train_v2.jsonl",
    "--eval-data", "castle_ex_dataset_layer2_lora_eval_v2.jsonl",
    "--output-dir", $outputDir,
    "--lora-r", "16",
    "--lora-alpha", "32",
    "--lora-dropout", "0.05",
    "--target-modules", "q_proj,k_proj,v_proj,o_proj",
    "--max-length", "512",
    "--batch-size", "2",
    "--gradient-accumulation-steps", "8",
    "--learning-rate", "2e-4",
    "--max-steps", "$MaxSteps",
    "--save-steps", "100",
    "--eval-steps", "100",
    "--fp16",
    "--resume-from-checkpoint", "auto"
)

$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$now] restarting training to max_steps=$MaxSteps" | Add-Content $monitorLog -Encoding utf8
$proc = Start-Process -FilePath "py.exe" -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
"[$now] relaunched pid=$($proc.Id) stdout=$stdoutPath stderr=$stderrPath" | Add-Content $monitorLog -Encoding utf8
