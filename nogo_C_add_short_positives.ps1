#!/usr/bin/env pwsh
# nogo_C_add_short_positives.ps1
# NO-GO C: hai再発 → 短文化正例を traindata に追加して再学習準備

param(
    [string]$GateDir       = "C:\Users\mana4\Desktop\manaos_integrations\Reports",
    [string]$GatePattern   = "gate_v117_ck300_*.json",
    [string]$BaseTrainData = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_7_train.jsonl",
    [string]$AuditData     = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl",
    [string]$OutputTrain   = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex_dataset_layer2_lora_v1_1_7_2_train.jsonl",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }

Write-Log "=== NO-GO C: 短文化正例追加 ========================"

# gate JSON確認
$gateFile = Get-ChildItem $GateDir -Filter $GatePattern | Sort-Object LastWriteTime -Desc | Select-Object -First 1
if ($gateFile) {
    $g = Get-Content $gateFile.FullName -Encoding UTF8 | ConvertFrom-Json
    Write-Log "gate: $($gateFile.Name) | hai=$($g.contains_hai)"
}

# audit100 から「hai」が含まれるNG例を抽出
$auditLines = Get-Content $AuditData -Encoding UTF8
$haiNgLines = $auditLines | Where-Object {
    $o = $_ | ConvertFrom-Json -EA SilentlyContinue
    $o -and ($o.PSObject.Properties['generated'] -or $o.PSObject.Properties['output']) -and
    ($o.generated -match "はい$|^はい" -or $o.output -match "はい$|^はい")
}
Write-Log "hai NG examples found: $($haiNgLines.Count)"

# 短文化正例テンプレートをベースに生成（実際は人手で確認推奨）
$shortPositives = @()
$haiNgLines | Select-Object -First 10 | ForEach-Object {
    $o = $_ | ConvertFrom-Json -EA SilentlyContinue
    if (-not $o) { return }
    $input = if ($o.PSObject.Properties['input']) { $o.input } else { "" }
    $short = [PSCustomObject]@{
        input    = $input
        output   = "（短文で明確に回答）"
        positive = $true
        _note    = "nogo_C_short_placeholder - 要人手確認・編集"
    }
    $shortPositives += ($short | ConvertTo-Json -Compress)
}

Write-Log "短文正例プレースホルダー: $($shortPositives.Count) 件"
Write-Log "[重要] _note='nogo_C_short_placeholder' の output は人手で編集必要"

$baseLines = Get-Content $BaseTrainData -Encoding UTF8
$merged    = ($baseLines + $shortPositives) | Where-Object { $_.Trim() -ne "" }
Write-Log "マージ後: $($merged.Count) 件 → $OutputTrain"

if (-not $DryRun) {
    $merged | Set-Content $OutputTrain -Encoding UTF8
    Write-Log "書き出し完了 → output を編集してから retrain してください"
}
