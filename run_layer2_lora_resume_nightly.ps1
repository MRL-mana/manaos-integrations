$ErrorActionPreference = "Stop"

$root = "C:\Users\mana4\Desktop\manaos_integrations"
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir "layer2_lora_nightly_$timestamp.log"

$alreadyRunning = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*train_castle_ex_lora.py*" }

if ($alreadyRunning) {
    "[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] training already running" | Out-File -FilePath $logPath -Encoding utf8
    exit 0
}

Set-Location $root

$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TQDM_DISABLE = "1"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

$args = @(
    "-3.10",
    "castle_ex\train_castle_ex_lora.py",
    "--base-model", "D:\castle_ex_training\castle_ex_v1_1",
    "--train-data", "castle_ex_dataset_layer2_lora_train_v2.jsonl",
    "--eval-data", "castle_ex_dataset_layer2_lora_eval_v2.jsonl",
    "--output-dir", "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_2",
    "--lora-r", "16",
    "--lora-alpha", "32",
    "--lora-dropout", "0.05",
    "--target-modules", "q_proj,k_proj,v_proj,o_proj",
    "--max-length", "512",
    "--batch-size", "2",
    "--gradient-accumulation-steps", "8",
    "--learning-rate", "2e-4",
    "--max-steps", "4000",
    "--save-steps", "100",
    "--eval-steps", "100",
    "--fp16",
    "--resume-from-checkpoint", "auto"
)

"[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] start training" | Out-File -FilePath $logPath -Encoding utf8
& py @args *>> $logPath
$exitCode = $LASTEXITCODE
"[$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")] exit_code=$exitCode" | Add-Content -Path $logPath -Encoding utf8
exit $exitCode
