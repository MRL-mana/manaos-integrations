param(
    [int]$IntervalSeconds = 120,
    [int]$CheckpointStep = 4000
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
$monitorLog = Join-Path $logDir "monitor_ck${CheckpointStep}_then_eval_$timestamp.log"
$stdoutPath = Join-Path $logDir "layer2_quick_eval_ck${CheckpointStep}_$timestamp.stdout.log"
$stderrPath = Join-Path $logDir "layer2_quick_eval_ck${CheckpointStep}_$timestamp.stderr.log"

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] start monitor: ckPath=$ckPath interval=$IntervalSeconds" | Add-Content $monitorLog -Encoding utf8

while ($true) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $ckExists = Test-Path $ckPath
    "[$now] ck_exists=$ckExists" | Add-Content $monitorLog -Encoding utf8
    if ($ckExists) {
        "[$now] [TRIGGER_DETECTED] checkpoint-$CheckpointStep exists" | Add-Content $monitorLog -Encoding utf8
        break
    }
    Start-Sleep -Seconds $IntervalSeconds
}

# ファイル書き込みが落ち着くのを少し待つ
Start-Sleep -Seconds 20

Set-Location $root
$env:PYTHONUNBUFFERED = "1"

$cmd = @(
    "-3.10",
    "-u",
    "run_layer2_quick_eval.py",
    "--checkpoint-step",
    "$CheckpointStep"
)

$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$now] running layer2 quick eval: py.exe $($cmd -join ' ')" | Add-Content $monitorLog -Encoding utf8

$proc = Start-Process -FilePath "py.exe" -ArgumentList $cmd -WorkingDirectory $root -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
"[$now] launched eval pid=$($proc.Id) stdout=$stdoutPath stderr=$stderrPath" | Add-Content $monitorLog -Encoding utf8
