<#
.SYNOPSIS
  V1.1.7 運用監視: 毎日20件ランダム監査 → Reports/daily_audit_*.json に保存
  タスクスケジューラーや手動実行で使う。

.DESCRIPTION
  audit100 JSONL からランダム20件を抽出し Layer2 推論サーバー (port 9520) に
  リクエスト → 正答率・hai率・repeat率を計算して JSON 保存。
  acc < 0.75 または hai > 5 または repeat > 3 で ALERT を表示。
  
.PARAMETER N
  抽出件数 (デフォルト 20)
.PARAMETER Port
  推論サーバーポート (デフォルト 9520)
.PARAMETER AuditJsonl
  監査元 JSONL パス
#>
param(
    [int]$N = 20,
    [int]$Port = 9520,
    [string]$AuditJsonl = "castle_ex_dataset_layer2_lora_v1_1_6_audit100.jsonl"
)
$ErrorActionPreference = "Stop"
$baseDir = $PSScriptRoot
Set-Location $baseDir

# ── 前提確認 ──────────────────────────────────────────────────────────────────
if (-not (Test-Path $AuditJsonl)) {
    Write-Error "[ERROR] Audit JSONL not found: $AuditJsonl"; exit 1
}

# サーバー疎通確認
try {
    $health = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 5
    Write-Host "[OK] Layer2 server alive (port $Port)"
} catch {
    Write-Host "[WARN] Layer2 server not responding on port $Port - starting stub check only"
    $Port = $null
}

# ── データ読み込み & ランダム抽出 ─────────────────────────────────────────────
$all = Get-Content $AuditJsonl | ForEach-Object { $_ | ConvertFrom-Json }
$sample = $all | Get-Random -Count ([Math]::Min($N, $all.Count))

Write-Host "[INFO] Sampling $($sample.Count) / $($all.Count) items..."

# ── 推論 & 評価 ───────────────────────────────────────────────────────────────
$results = @()
$correct = 0
$hai_count = 0
$repeat_count = 0

foreach ($item in $sample) {
    $prompt  = $item.prompt
    $gold    = if ($item.completion) { $item.completion.Trim() } else { $item.output.Trim() }
    $pair_id = if ($item.pair_id) { $item.pair_id } else { "" }
    $tmpl_id = if ($item.template_id) { $item.template_id } else { "" }

    if ($Port) {
        try {
            $body = @{
                prompt      = $prompt
                mode        = "short"
                max_new_tokens = 64
                do_sample   = $false
                gold        = $gold   # NG自動記録用
                pair_id     = $pair_id
                template_id = $tmpl_id
            } | ConvertTo-Json -Compress
            $resp = Invoke-RestMethod "http://127.0.0.1:$Port/generate" `
                -Method POST -Body $body -ContentType "application/json; charset=utf-8" `
                -TimeoutSec 30
            $pred = $resp.text.Trim()
        } catch {
            $pred = "[ERROR: $($_.Exception.Message)]"
        }
    } else {
        $pred = "[SKIP: server offline]"
    }

    $ok = ($pred.ToLower() -eq $gold.ToLower())
    if ($ok) { $correct++ }

    # hai チェック (はい/いいえ の誤出力)
    if ($gold -notmatch "^はい|^いいえ" -and $pred -match "^はい|^いいえ") { $hai_count++ }

    # repeat チェック (3語以上のフレーズ繰り返し)
    $words = $pred -split "\s+"
    $has_repeat = $false
    if ($words.Count -ge 6) {
        for ($i = 0; $i -lt $words.Count - 3; $i++) {
            $phrase = "$($words[$i]) $($words[$i+1]) $($words[$i+2])"
            $rest = ($words[($i+3)..($words.Count-1)] -join " ")
            if ($rest -match [regex]::Escape($phrase)) { $has_repeat = $true; break }
        }
    }
    if ($has_repeat) { $repeat_count++ }

    $results += [PSCustomObject]@{
        pair_id     = $pair_id
        template_id = $tmpl_id
        gold        = $gold
        pred        = $pred
        ok          = $ok
    }
}

$acc = [math]::Round($correct / $sample.Count, 4)

# ── アラート判定 ──────────────────────────────────────────────────────────────
$status = "PASS"
$alerts = @()
if ($acc -lt 0.75) { $alerts += "acc=$acc < 0.75"; $status = "ALERT" }
if ($hai_count -gt 5) { $alerts += "hai=$hai_count > 5"; $status = "ALERT" }
if ($repeat_count -gt 3) { $alerts += "repeat=$repeat_count > 3"; $status = "ALERT" }

Write-Host ""
Write-Host "==== Mini Audit Result ===="
Write-Host "  acc    : $acc ($correct/$($sample.Count))"
Write-Host "  hai    : $hai_count"
Write-Host "  repeat : $repeat_count"
Write-Host "  status : $status"
if ($alerts) { Write-Host "  ALERTS : $($alerts -join ' | ')" -ForegroundColor Red }
Write-Host "==========================="

# ── JSON 保存 ─────────────────────────────────────────────────────────────────
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = "Reports\daily_audit_$ts.json"
if (-not (Test-Path Reports)) { New-Item -ItemType Directory Reports | Out-Null }

@{
    timestamp   = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    n           = $sample.Count
    accuracy    = $acc
    correct     = $correct
    hai         = $hai_count
    repeat      = $repeat_count
    status      = $status
    alerts      = $alerts
    details     = $results
} | ConvertTo-Json -Depth 5 | Set-Content $outFile -Encoding UTF8

Write-Host "[SAVED] $outFile"

# V1.1.8 開始条件チェック
$ng_count = ($results | Where-Object { -not $_.ok }).Count
if ($ng_count -ge 5) {
    Write-Host ""
    Write-Host "[HINT] NG=$ng_count 件 → 同型NG5件以上。V1.1.8 の開始条件を満たしています。" -ForegroundColor Yellow
    Write-Host "  → nogo_A_inject_and_retrain.ps1 を参照"
}
