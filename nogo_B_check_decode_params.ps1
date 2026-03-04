#!/usr/bin/env pwsh
# nogo_B_check_decode_params.ps1
# NO-GO B: repeat再発 → デコードパラメータを強制確認・パッチ

param(
    [string]$InferServerPy = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex\castle_ex_layer2_inference_server.py",
    [string]$ServicePy     = "C:\Users\mana4\Desktop\manaos_integrations\castle_ex\castle_ex_layer2_service.py"
)
$ErrorActionPreference = "Stop"
function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" }

Write-Log "=== NO-GO B: デコードパラメータ確認 ========================"

# max_new_tokens 確認
$mnFiles = @($InferServerPy, $ServicePy)
foreach ($f in $mnFiles) {
    $hits = Select-String -Path $f -Pattern "max_new_tokens" | Select-Object LineNumber, Line
    Write-Log "[$([System.IO.Path]::GetFileName($f))] max_new_tokens:"
    $hits | ForEach-Object { Write-Log "  L$($_.LineNumber): $($_.Line.Trim())" }
}

# no_repeat_ngram_size 確認
Write-Log ""; Write-Log "no_repeat_ngram_size:"
foreach ($f in $mnFiles) {
    $hits = Select-String -Path $f -Pattern "no_repeat_ngram_size" | Select-Object LineNumber, Line
    Write-Log "[$([System.IO.Path]::GetFileName($f))]"
    $hits | ForEach-Object { Write-Log "  L$($_.LineNumber): $($_.Line.Trim())" }
}

# 期待値チェック
$hasMaxTokens64 = (Select-String -Path $InferServerPy -Pattern "max_new_tokens.*64|64.*max_new_tokens" -Quiet)
$hasNgram3      = (Select-String -Path $InferServerPy -Pattern "no_repeat_ngram_size.*3"             -Quiet)
$hasRepPenalty  = (Select-String -Path $ServicePy     -Pattern "repetition_penalty.*1\.1"            -Quiet)

Write-Log ""
Write-Log "チェック結果:"
Write-Log "  max_new_tokens=64 固定  : $($hasMaxTokens64 -eq $true)"
Write-Log "  no_repeat_ngram_size=3  : $($hasNgram3 -eq $true)"
Write-Log "  repetition_penalty=1.1  : $($hasRepPenalty -eq $true)"

if (-not $hasMaxTokens64 -or -not $hasNgram3 -or -not $hasRepPenalty) {
    Write-Log ""
    Write-Log "[WARNING] パラメータが期待値と一致しない箇所があります。"
    Write-Log "castle_ex_layer2_service.py の gen_kwargs を確認してください。"
    exit 2
} else {
    Write-Log "[OK] デコードパラメータ全て正常"
    Write-Log "repeat の原因は学習データにある可能性 → audit100 repeat例を確認推奨"
}
