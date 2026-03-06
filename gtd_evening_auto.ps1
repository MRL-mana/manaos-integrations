# GTD Evening Auto Routine
# 毎晩自動実行: 今日の完了タスク集計 + 明日Top1 + 気づき抽出 + Slack通知
# TaskScheduler: ManaOS_GTD_Evening_Auto (21:00 毎日)
param(
    [string]$Date    = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$Notify  = $true,
    [switch]$Stdout
)

$root   = "C:\Users\mana4\Desktop\manaos_integrations"
$logDir = "$root\gtd\daily-logs"
$logFile = "$logDir\$Date.md"

# ---- 日次ログ読み込み ----
function Get-Section {
    param([string[]]$Lines, [string]$Header)
    $out   = @()
    $inside = $false
    foreach ($l in $Lines) {
        if ($l -match "^## $Header") { $inside = $true; continue }
        if ($inside -and $l -match "^## ") { break }
        if ($inside) { $out += $l }
    }
    return ($out | Where-Object { $_.Trim() -ne "" -and $_.Trim() -ne "-" })
}

$doneLines     = @()
$insightLines  = @()
$tomorrowLines = @()
$top3Lines     = @()

if (Test-Path $logFile) {
    $allLines      = Get-Content $logFile
    $doneLines     = Get-Section $allLines "完了タスク"
    $insightLines  = Get-Section $allLines "気づき・メモ"
    $tomorrowLines = Get-Section $allLines "明日への申し送り"
    $top3Lines     = Get-Section $allLines "今日の3大優先事項"
} else {
    Write-Host "[GTD Evening] 日次ログなし: $logFile"
}

# ---- 完了タスク数と表示（最大5件）----
$doneCount = $doneLines.Count
$doneText  = if ($doneCount -gt 0) {
    ($doneLines | Select-Object -First 5 | ForEach-Object { "  • $($_.TrimStart('- ').TrimStart('* '))" }) -join "`n"
} else { "  （記録なし — 日次ログに書いておこう）" }

# ---- 明日Top1（申し送り1行目）----
$tomorrowTop = if ($tomorrowLines.Count -gt 0) {
    $tomorrowLines[0].TrimStart("- ").TrimStart("* ").Trim()
} else { "未設定" }

# ---- 気づき1行（最初の1行）----
$insightTop = if ($insightLines.Count -gt 0) {
    $insightLines[0].TrimStart("- ").TrimStart("* ").Trim()
} else { "記録なし" }

# ---- 達成率（Top3 vs 完了）----
$top3Count  = ($top3Lines | Where-Object { $_ -match "^\d+\." -or $_ -match "^[- *]" }).Count
$achievement = if ($top3Count -gt 0) {
    $pct = [int]([math]::Min($doneCount, $top3Count) / $top3Count * 100)
    "${pct}%（完了: ${doneCount} / 予定: ${top3Count}）"
} else { "（3大優先未設定）" }

# ---- コンソール出力 ----
Write-Host ""
Write-Host "============================================"
Write-Host " GTD Evening Routine — $Date"
Write-Host "============================================"
Write-Host " 完了タスク : $doneCount 件"
Write-Host " 達成率     : $achievement"
Write-Host " 明日Top1   : $tomorrowTop"
Write-Host " 気づき     : $insightTop"
Write-Host "============================================"

# ---- 通知送信ヘルパー (Slack → ntfy.sh 自動フォールバック) ----
function Send-ManaOSNotify {
    param([string]$Title, [string]$Body)

    # 1) Slack Webhook
    $slackUrl = [System.Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")
    if (-not $slackUrl) { $slackUrl = $env:SLACK_WEBHOOK_URL }
    if ($slackUrl) {
        try {
            $msg = @{ text = "*$Title*`n$Body" } | ConvertTo-Json
            Invoke-RestMethod -Uri $slackUrl -Method POST -Body $msg -ContentType "application/json" -TimeoutSec 5 | Out-Null
            Write-Host "[GTD Evening] 通知: Slack OK"
            return
        } catch { Write-Host "[GTD Evening] Slack: NG → ntfy にフォールバック" }
    }

    # 2) ntfy.sh フォールバック
    $ntfyTopic = [System.Environment]::GetEnvironmentVariable("NTFY_TOPIC", "User")
    if (-not $ntfyTopic) { $ntfyTopic = $env:NTFY_TOPIC }
    if (-not $ntfyTopic) { $ntfyTopic = "manaos-$(hostname)" }
    try {
        python -c "
import urllib.request, sys
req = urllib.request.Request(
    'https://ntfy.sh/$ntfyTopic',
    data=sys.argv[1].encode('utf-8'),
    method='POST',
    headers={'Title': sys.argv[2].encode('utf-8').decode('ascii','replace'), 'Priority': 'default', 'Tags': 'night_with_stars', 'Content-Type': 'text/plain; charset=utf-8'}
)
urllib.request.urlopen(req, timeout=8)
print('ntfy OK')
" "$Body" "$Title" 2>&1 | ForEach-Object { Write-Host "[GTD Evening] ntfy: $_" }
    } catch { Write-Host "[GTD Evening] ntfy: NG ($($_.Exception.Message))" }
}

# ── GTD日次ログを git commit --push ────────────────────────────────────────
Write-Host "[GTD Evening] GTD変更を git commit..."
$commitOut = & python "$PSScriptRoot\tools\manaosctl.py" gtd commit --push 2>&1
$commitOut | ForEach-Object { Write-Host "[GTD Evening] commit: $_" }

if ($Notify) {
    $title = "ManaOS Evening $Date"
    $body  = "完了: $doneCount 件 ($achievement)`n$doneText`n`n明日Top1: $tomorrowTop`n気づき: $insightTop"
    Send-ManaOSNotify -Title $title -Body $body
} else {
    Write-Host "[GTD Evening] 通知: スキップ（-Notify:\$false）"
}
