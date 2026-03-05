# GTD Weekly Auto Routine
# 毎週日曜自動実行: 先週の振り返り + Inbox/Next Actions 集計 + ntfy 通知
# TaskScheduler: ManaOS_GTD_Weekly_Auto (毎週日曜 21:30)
param(
    [switch]$Notify = $true,
    [switch]$Stdout
)

$root      = "C:\Users\mana4\Desktop\manaos_integrations"
$python    = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"
$ctl       = "$root\tools\manaosctl.py"
$logDir    = "$root\gtd\daily-logs"
$today     = Get-Date
$weekStart = $today.AddDays(-6)
$rangeStr  = "$($weekStart.ToString('MM/dd'))-$($today.ToString('MM/dd'))"

# ---- 先週7日分のログを収集 ----
$allLogs = @()
for ($i = 6; $i -ge 0; $i--) {
    $d    = $today.AddDays(-$i).ToString("yyyy-MM-dd")
    $file = "$logDir\$d.md"
    if (Test-Path $file) { $allLogs += [PSCustomObject]@{ Date = $d; File = $file } }
}

# ---- 各ログから完了タスクを収集 ----
function Get-Section {
    param([string[]]$Lines, [string]$Header)
    $out    = @()
    $inside = $false
    foreach ($l in $Lines) {
        if ($l -match "^## $Header")    { $inside = $true; continue }
        if ($inside -and $l -match "^## ") { break }
        if ($inside)                     { $out += $l }
    }
    return ($out | Where-Object { $_.Trim() -ne "" -and $_.Trim() -ne "-" })
}

$totalDone    = 0
$dayRecords   = @()
$allInsights  = @()

foreach ($log in $allLogs) {
    $lines    = Get-Content $log.File -ErrorAction SilentlyContinue
    $done     = Get-Section $lines "完了タスク"
    $insights = Get-Section $lines "気づき・メモ"
    $totalDone += $done.Count
    $dayRecords   += [PSCustomObject]@{ Date = $log.Date; DoneCount = $done.Count }
    foreach ($ins in ($insights | Select-Object -First 2)) {
        $allInsights += "[$($log.Date)] $($ins.TrimStart('- ').TrimStart('* ').Trim())"
    }
}

# ---- Inbox / Next Actions 現況 ----
$inboxDir = "$root\gtd\inbox"
$naDir    = "$root\gtd\next-actions"
$inboxN   = if (Test-Path $inboxDir) { (Get-ChildItem "$inboxDir\*.md" -ErrorAction SilentlyContinue | Where-Object { $_.Name.ToUpper() -ne "README.MD" }).Count } else { 0 }
$naN      = if (Test-Path $naDir)    { (Get-ChildItem "$naDir\*.md"    -ErrorAction SilentlyContinue | Where-Object { $_.Name.ToUpper() -ne "README.MD" }).Count } else { 0 }

# ---- 平均完了タスク / 最多日 ----
$avgDone  = if ($allLogs.Count -gt 0) { [math]::Round($totalDone / $allLogs.Count, 1) } else { 0 }
$bestDay  = $dayRecords | Sort-Object DoneCount -Descending | Select-Object -First 1
$logDays  = $allLogs.Count

# ---- コンソール出力 ----
$rangeStr = "$($weekStart.ToString('MM/dd'))〜$($today.ToString('MM/dd'))"
Write-Host ""
Write-Host "============================================"
Write-Host " GTD Weekly Review — $rangeStr"
Write-Host "============================================"
Write-Host " 記録日数       : $logDays 日 / 7日"
Write-Host " 週合計完了     : $totalDone タスク"
Write-Host " 1日平均完了    : $avgDone タスク"
if ($bestDay) { Write-Host " 最多完了日     : $($bestDay.Date)  $($bestDay.DoneCount) タスク" }
Write-Host " Inbox 現況     : $inboxN 件"
Write-Host " Next Actions   : $naN 件"
if ($allInsights.Count -gt 0) {
    Write-Host ""
    Write-Host " --- 今週の気づき (最大3件) ---"
    $allInsights | Select-Object -First 3 | ForEach-Object { Write-Host "  • $_" }
}
Write-Host "============================================"

# ---- 通知送信ヘルパー (Slack → ntfy.sh 自動フォールバック) ----
function Send-ManaOSNotify {
    param([string]$Title, [string]$Body, [string]$Tags = "calendar")

    # 1) Slack Webhook
    $slackUrl = [System.Environment]::GetEnvironmentVariable("SLACK_WEBHOOK_URL", "User")
    if (-not $slackUrl) { $slackUrl = $env:SLACK_WEBHOOK_URL }
    if ($slackUrl) {
        try {
            $msg = @{ text = "*$Title*`n$Body" } | ConvertTo-Json
            Invoke-RestMethod -Uri $slackUrl -Method POST -Body $msg -ContentType "application/json" -TimeoutSec 5 | Out-Null
            Write-Host "[GTD Weekly] 通知: Slack OK"
            return
        } catch { Write-Host "[GTD Weekly] Slack: NG → ntfy にフォールバック" }
    }

    # 2) ntfy.sh フォールバック — 環境変数経由で日本語対応
    $ntfyTopic = [System.Environment]::GetEnvironmentVariable("NTFY_TOPIC", "User")
    if (-not $ntfyTopic) { $ntfyTopic = $env:NTFY_TOPIC }
    if (-not $ntfyTopic) { $ntfyTopic = "manaos-$(hostname)" }
    try {
        $env:MANAOS_NOTIFY_BODY = $Body
        python -c "
import os, urllib.request
body  = os.environ.get('MANAOS_NOTIFY_BODY', '').encode('utf-8')
topic = os.environ.get('NTFY_TOPIC', 'manaos-default')
req   = urllib.request.Request(
    f'https://ntfy.sh/{topic}', data=body, method='POST',
    headers={
        'Title':        'ManaOS Weekly Report',
        'Priority':     'default',
        'Tags':         'calendar',
        'Content-Type': 'text/plain; charset=utf-8',
    }
)
urllib.request.urlopen(req, timeout=8)
print('ntfy OK')
" 2>&1 | ForEach-Object { Write-Host "[GTD Weekly] ntfy: $_" }
    } catch { Write-Host "[GTD Weekly] ntfy: NG ($($_.Exception.Message))" }
    finally { Remove-Item Env:\MANAOS_NOTIFY_BODY -ErrorAction SilentlyContinue }
}

if ($Notify) {
    $insightStr = if ($allInsights.Count -gt 0) {
        "`n気づき: " + (($allInsights | Select-Object -First 2) -join " / ")
    } else { "" }
    $bestStr = if ($bestDay) { " (最多: $($bestDay.Date) $($bestDay.DoneCount)件)" } else { "" }
    $body  = "記録 $logDays/7日 | 完了 $totalDone タスク (平均 $avgDone/日)$bestStr`nInbox: $inboxN件 / Next: $naN件$insightStr"
    Send-ManaOSNotify -Title "ManaOS Weekly $rangeStr" -Body $body -Tags "calendar"
} else {
    Write-Host "[GTD Weekly] 通知: スキップ（-Notify:`$false）"
}
