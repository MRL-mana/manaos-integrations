param(
    [string]$SrcDir   = "D:\castle_ex_training\lora_castle_ex_layer2_v1_1_7_patch",
    [int]$CheckpointStep = 300,
    [string]$ProdDir  = "D:\castle_ex_training\lora_castle_ex_layer2_prod",
    [string]$BackupRoot = "D:\castle_ex_training\_prod_backups",
    [string]$Version  = "v1.1.7"
)
$ErrorActionPreference = "Stop"

# checkpoint-N サブディレクトリを優先（なければrootを使う）
$ckPath = Join-Path $SrcDir "checkpoint-$CheckpointStep"
$srcAdapter = if (Test-Path $ckPath) { $ckPath } else { $SrcDir }
Write-Host "[src] using adapter from: $srcAdapter"

# 1. バックアップ（上書き前に旧prodを保存）
$ts     = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $BackupRoot "lora_castle_ex_layer2_prod_before_${Version}_$ts"
Write-Host "[1/4] backing up current prod → $backup"
Copy-Item $ProdDir $backup -Recurse -Force
Write-Host "      backup OK"

# 2. v1.1.7 の adapter ファイルを prod に上書き
#    （safetensors + config のみ。optimizer/scheduler は prod に入れない）
$copyTargets = @("adapter_model.safetensors","adapter_config.json","tokenizer_config.json","special_tokens_map.json","tokenizer.model")
Write-Host "[2/4] copying adapter files: $($copyTargets -join ', ')"
foreach ($f in $copyTargets) {
    $src = Join-Path $srcAdapter $f
    if (Test-Path $src) {
        Copy-Item $src $ProdDir -Force
        Write-Host "      copied: $f"
    }
}

# 3. prod ディレクトリの README 更新
$readmePath = Join-Path $ProdDir "PROD_VERSION.txt"
"${Version} - checkpoint-${CheckpointStep} - updated $(Get-Date -Format 's')`nSrc: $srcAdapter`nBackup: $backup" | Set-Content $readmePath -Encoding UTF8
Write-Host "[3/4] PROD_VERSION.txt updated"

# 4. 確認
Write-Host "[4/4] prod dir contents:"
Get-ChildItem $ProdDir | Select-Object Name, @{n='KB';e={[math]::Round($_.Length/1KB,0)}}, LastWriteTime

Write-Host "`n[DONE] prod adapter updated to $Version (from checkpoint-$CheckpointStep)"
Write-Host "       src: $srcAdapter"
Write-Host "       run regression audit next:"
Write-Host "  py -3.10 scripts\run\run_layer2_quick_eval.py --base-model D:\castle_ex_training\castle_ex_v1_1 --output-dir $SrcDir --checkpoint-step $CheckpointStep --eval-data castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl --device-map cuda:0 --reports-dir Reports --max-new-tokens 64"
