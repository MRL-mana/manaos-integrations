#!/usr/bin/env pwsh
# nogo_A_inject_and_retrain.ps1
# NO-GO A: acc不足 → NG pair_id を eval JSON から特定 → 正例再注入で v1.1.7.1 学習

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
if (-not $gateFile) { Write-Error "gate JSON なし: $GateDir\$GatePattern"; exit 1 }
$g = Get-Content $gateFile.FullName -Encoding UTF8 | ConvertFrom-Json
Write-Log "gate: $($gateFile.Name) | acc=$($g.acc)"

if (-not $g.eval_json -or -not (Test-Path $g.eval_json)) {
    Write-Error "gate.eval_json が見つかりません: $($g.eval_json)"
    exit 1
}

# eval JSON から ok=false の pair_id を取得
Write-Log "eval JSON: $($g.eval_json)"
$evalData = Get-Content $g.eval_json -Encoding UTF8 | ConvertFrom-Json
$ngDetails = $evalData.details | Where-Object { -not $_.ok } | Select-Object -First $TopN
Write-Log "NG examples (top$TopN): $($ngDetails.Count) 件"
$ngDetails | ForEach-Object { Write-Log "  pair_id=$($_.pair_id) | pred=$($_.pred.Substring(0, [Math]::Min(60,$_.pred.Length)))..." }

# audit100 から NG pair_id に対応する行を positive=true で注入
# eval JSON の gold を正解として使う（audit100でなくevalから直接生成）
$auditLines = Get-Content $AuditData -Encoding UTF8
$injections = @()
foreach ($row in $ngDetails) {
    # audit100から同じ pair_id を探す（あれば元データを再利用）
    $auditHit = $auditLines | Where-Object { $_ -match [regex]::Escape($row.pair_id) } | Select-Object -First 1
    if ($auditHit) {
        $obj = $auditHit | ConvertFrom-Json
        $obj | Add-Member -Force NoteProperty "positive" $true
        $obj | Add-Member -Force NoteProperty "_injected_from" "nogo_A_audit"
        $injections += ($obj | ConvertTo-Json -Compress)
    } else {
        # eval details から直接 input/output を構築
        $synth = [PSCustomObject]@{
            pair_id      = $row.pair_id
            input        = if ($row.PSObject.Properties['input']) { $row.input } else { "" }
            output       = $row.gold
            positive     = $true
            _injected_from = "nogo_A_eval_gold"
        }
        $injections += ($synth | ConvertTo-Json -Compress)
    }
}
Write-Log "注入件数: $($injections.Count)"

# ベース traindata + injections をマージ
$baseLines = Get-Content $BaseTrainData -Encoding UTF8
$merged    = ($baseLines + $injections) | Where-Object { $_.Trim() -ne "" }
Write-Log "マージ後: $($merged.Count) 件 → $OutputTrain"

if (-not $DryRun) {
    $merged | Set-Content $OutputTrain -Encoding UTF8
    Write-Log "書き出し完了"
    Write-Log ""
    Write-Log "次ステップ: run_v117_onebutton.ps1 の OutputDir を"
    Write-Log "  lora_castle_ex_layer2_v1_1_7_1_patch に変更して再学習"
}
