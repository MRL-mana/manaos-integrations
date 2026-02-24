#!/usr/bin/env pwsh
# v1.1.3: checkpoint-3000検知→Layer2軽量評価自動実行
param(
    [int]$IntervalSeconds = 120
)

$ckPath = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3\checkpoint-3000"
$logDir = "$PSScriptRoot\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "monitor_ck3000_v113_then_eval_$timestamp.log"

function Log-Message {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

Log-Message "start monitor: ckPath=$ckPath interval=$IntervalSeconds"

while ($true) {
    $exists = Test-Path $ckPath
    Log-Message "ck_exists=$exists"
    
    if ($exists) {
        Log-Message "[TRIGGER_DETECTED] checkpoint-3000 exists"
        Start-Sleep -Seconds 40
        
        $evalCmd = "py.exe -3.10 -u run_layer2_quick_eval.py --checkpoint-step 3000 --output-dir D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3 --eval-data castle_ex_dataset_layer2_lora_v1_1_3_eval.jsonl"
        Log-Message "running layer2 quick eval: $evalCmd"
        
        $stdoutLog = Join-Path $logDir "layer2_quick_eval_ck3000_v113_$timestamp.stdout.log"
        $stderrLog = Join-Path $logDir "layer2_quick_eval_ck3000_v113_$timestamp.stderr.log"
        
        $proc = Start-Process -FilePath "py.exe" `
            -ArgumentList "-3.10", "-u", "run_layer2_quick_eval.py", "--checkpoint-step", "3000", "--output-dir", "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3", "--eval-data", "castle_ex_dataset_layer2_lora_v1_1_3_eval.jsonl" `
            -WorkingDirectory $PSScriptRoot `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog `
            -PassThru
        
        Log-Message "launched eval pid=$($proc.Id) stdout=$stdoutLog stderr=$stderrLog"
        break
    }
    
    Start-Sleep -Seconds $IntervalSeconds
}

Log-Message "monitor finished"
