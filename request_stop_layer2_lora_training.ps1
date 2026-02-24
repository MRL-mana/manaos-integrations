$ErrorActionPreference = "Stop"

# Stop request for CASTLE-EX Layer2 LoRA training
# Training script watches for this file and will: save checkpoint on step end -> stop -> delete the file.

$outputDir = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_2"
$stopFile = Join-Path $outputDir "STOP_TRAINING"

if (-not (Test-Path $outputDir)) {
    throw "outputDir not found: $outputDir"
}

New-Item -ItemType File -Path $stopFile -Force | Out-Null
"STOP requested: $stopFile"
