#!/usr/bin/env pwsh
# nogo_A_inject_and_retrain.ps1
# NO-GO A: acc不足 → NG pair_id 上位を正例再注入して v1.1.7.1 patch 学習

param(
    [string]$GateDir       = "C:\Users\mana4\Desktop\manaos_integrations\Reports",
    [string]$GatePattern   = "gate_v117_ck300_*.json",
    [string]$BaseTrainData = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_7_train.jsonl",
    [string]$AuditData     = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl",
    [string]$OutputTrain   = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_7_1_train.jsonl",
    [int]   $TopN          = 10,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }

# 最新 gate JSON 取得
$gateFile = Get-ChildItem $GateDir -Filter $GatePattern | Sort-Object LastWriteTime -Desc | Select-Object -First 1
if (-not $gateFile) { Write-Error "gate JSON なし"; exit 1 }
$g = Get-Content $gateFile.FullName -Encoding UTF8 | ConvertFrom-Json
Write-Log "gate: $($gateFile.Name) | acc=$($g.acc)"

# failed_ids からNG例特定（gate JSONに failed_ids[] がある場合）
$failedIds = @()
if ($g.PSObject.Properties['failed_ids']) { $failedIds = $g.failed_ids | Select-Object -First $TopN }
Write-Log "NG pair_ids (top$TopN): $($failedIds -join ', ')"

# audit100からNG行を抽出して正例タグ付け
$auditLines = Get-Content $AuditData -Encoding UTF8
$injections = @()
foreach ($id in $failedIds) {
    $hit = $auditLines | Where-Object { $_ -match "`"pair_id`"\s*:\s*`"$id`"" } | Select-Object -First 1
    if ($hit) {
        $obj = $hit | ConvertFrom-Json
        $obj | Add-Member -Force NoteProperty "positive" $true
        $obj | Add-Member -Force NoteProperty "_injected_from" "nogo_A"
        $injections += ($obj | ConvertTo-Json -Compress)
    }
}
Write-Log "注入候補: $($injections.Count) 件"

# ベース traindata + injections を v1.1.7.1 用に合成
$baseLines = Get-Content $BaseTrainData -Encoding UTF8
$merged = ($baseLines + $injections) | Where-Object { $_.Trim() -ne "" }
Write-Log "マージ後: $($merged.Count) 件 → $OutputTrain"

if (-not $DryRun) {
    $merged | Set-Content $OutputTrain -Encoding UTF8
    Write-Log "書き出し完了"
    Write-Log ""
    Write-Log "次ステップ: run_v117_patch1_onebutton.ps1 を実行してください"
    Write-Log "  (SrcDir, OutputDir を v1.1.7.1 に差し替えてから)"
}
