#!/usr/bin/env pwsh
# auto_gate_check_and_deploy_v117.ps1
# gate JSON が現れたら GO/NO-GO を自動判定し、GOなら prod を差し替える
# 使い方:
#   powershell -ExecutionPolicy Bypass -File .\auto_gate_check_and_deploy_v117.ps1
#   (バックグラウンド待機待ちではなく、手動でgate JSON確認後に呼ぶ想定)

param(
    [string]$GateDir       = "C:\Users\mana4\Desktop\manaos_integrations\Reports",
    [string]$GatePattern   = "gate_v117_ck300_*.json",
    [string]$Version       = "v1.1.7",
    [int]   $CheckpointStep = 300,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"

# ── 判定基準 ──────────────────────────────────────────
$GO_ACC_MIN          = 0.75
$NOGO_HAI_MAX        = 10
$NOGO_REPEAT_MAX     = 5

function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }

# ── 最新の gate JSON を探す ─────────────────────────────
$gates = Get-ChildItem $GateDir -Filter $GatePattern -EA SilentlyContinue |
         Sort-Object LastWriteTime -Descending

if (-not $gates) {
    Write-Log "gate JSON が見つかりません: $GateDir\$GatePattern"
    Write-Log "monitor_v117_ck300_*.ps1 が checkpoint-300 を eval する前に呼び出された可能性があります。"
    exit 1
}

$gateFile = $gates[0].FullName
Write-Log "gate JSON: $gateFile"
$g = Get-Content $gateFile -Encoding UTF8 | ConvertFrom-Json

# ── gate JSON 内容表示 ──────────────────────────────────
Write-Log "=== gate結果 =========================="
Write-Log "  acc              = $($g.acc)"
Write-Log "  contains_hai     = $($g.contains_hai)"
Write-Log "  contains_repeat  = $($g.contains_repeat_phrase)"
Write-Log "  passed           = $($g.passed)"
if ($g.PSObject.Properties['details']) { Write-Log "  details = $($g.details)" }
Write-Log "======================================="

# ── GO/NO-GO 判定 ──────────────────────────────────────
$acc     = [double]($g.acc)
$hai     = [int]($g.contains_hai)
$repeat  = [int]($g.contains_repeat_phrase)

if ($acc -ge $GO_ACC_MIN -and $hai -le $NOGO_HAI_MAX -and $repeat -le $NOGO_REPEAT_MAX) {
    Write-Log "[GO] 全条件クリア → prod 差し替え開始"

    if ($DryRun) {
        Write-Log "[DRY-RUN] update_prod_to_v117.ps1 をスキップ"
    } else {
        $script = Join-Path $PSScriptRoot "update_prod_to_v117.ps1"
        Write-Log "実行: $script -Version $Version -CheckpointStep $CheckpointStep"
        powershell -ExecutionPolicy Bypass -File $script `
            -Version $Version `
            -CheckpointStep $CheckpointStep
        Write-Log "[GO] prod 更新完了"
    }
    exit 0

} else {
    Write-Log "[NO-GO] 条件未達"

    # 原因分類
    if ($acc -lt $GO_ACC_MIN) {
        Write-Log ""
        Write-Log "[NO-GO A] acc=$acc < $GO_ACC_MIN"
        Write-Log "  → 対策: NG pair_id 上位10件を正例再注入してv1.1.7.1を学習"
        Write-Log "  → スクリプト: .\nogo_A_inject_and_retrain.ps1"
        Write-Log "  → NG例は gate JSON の failed_ids フィールド参照"
    }
    if ($repeat -gt $NOGO_REPEAT_MAX) {
        Write-Log ""
        Write-Log "[NO-GO B] contains_repeat_phrase=$repeat > $NOGO_REPEAT_MAX"
        Write-Log "  → 対策: max_new_tokens=64 固定確認、no_repeat_ngram_size=3 確認"
        Write-Log "  → スクリプト: .\nogo_B_check_decode_params.ps1"
    }
    if ($hai -gt $NOGO_HAI_MAX) {
        Write-Log ""
        Write-Log "[NO-GO C] contains_hai=$hai > $NOGO_HAI_MAX"
        Write-Log "  → 対策: 短文化正例追加 → retrain"
        Write-Log "  → スクリプト: .\nogo_C_add_short_positives.ps1"
    }
    exit 2
}
