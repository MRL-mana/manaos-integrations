# GTD Morning Auto Routine
# 毎朝自動実行: 日次ログ作成 + Inbox確認 + Next Actions ピックアップ + Obsidian保存 + Slack通知

param(
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [switch]$Notify = $true
)

$root    = Split-Path -Parent $PSScriptRoot
if (-not $root -or -not (Test-Path "$root\gtd")) {
    $root = "C:\Users\mana4\Desktop\manaos_integrations"
}

$logDir  = "$root\gtd\daily-logs"
$inboxDir= "$root\gtd\inbox"
$naDir   = "$root\gtd\next-actions\items"
$logFile = "$logDir\$Date.md"

New-Item -ItemType Directory -Force -Path $logDir  | Out-Null

# ---- GTD Capture Server 自動起動（port 5130）----
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5130/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[GTD Morning] Capture Server: 既に起動中"
} catch {
    Write-Host "[GTD Morning] Capture Server: 起動します..."
    Start-Process pwsh -ArgumentList "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\start_gtd_capture_server.ps1`"" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}
New-Item -ItemType Directory -Force -Path $inboxDir | Out-Null
New-Item -ItemType Directory -Force -Path $naDir    | Out-Null

# ---- 前日ログから申し送りを取得 ----
$yesterday   = (Get-Date $Date).AddDays(-1).ToString("yyyy-MM-dd")
$yLogFile    = "$logDir\$yesterday.md"
$carryover   = ""
if (Test-Path $yLogFile) {
    $lines = Get-Content $yLogFile
    $inCarry = $false
    foreach ($l in $lines) {
        if ($l -match "^## 明日への申し送り") { $inCarry = $true; continue }
        if ($inCarry -and $l -match "^## ") { break }
        if ($inCarry -and $l.Trim() -ne "") { $carryover += "  $l`n" }
    }
}
if (-not $carryover) { $carryover = "  （なし）`n" }

# ---- Inbox 件数 ----
$inboxCount = @(Get-ChildItem $inboxDir -Filter "*.md" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "README.md" }).Count
$inboxWarn  = if ($inboxCount -ge 10) { "  ⚠️ Inbox が $inboxCount 件溜まっています → `/inbox` で処理推奨`n" } else { "" }

# ---- Next Actions ピックアップ（最大5件）----
$naItems = @(Get-ChildItem $naDir -Filter "*.md" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "README.md" } | Sort-Object Name | Select-Object -First 5)
$naLines = if ($naItems.Count -gt 0) {
    ($naItems | ForEach-Object { "  - [ ] $($_.BaseName)" }) -join "`n"
} else { "  （Next Actions なし）" }

# ---- 日次ログ作成（既存なら上書きしない）----
if (-not (Test-Path $logFile)) {
    $content = @"
# $Date 日次ログ

## 今日の3大優先事項
1. 
2. 
3. 

## 昨日の申し送り
$carryover
## 今日のNext Actions候補
$naLines

## Inbox状況
  件数: $inboxCount 件
$inboxWarn
## 完了タスク
- 

## 気づき・メモ
- 

## 明日への申し送り
- 
"@
    Set-Content -Path $logFile -Value $content -Encoding UTF8
    Write-Host "[GTD Morning] 日次ログ作成: $logFile"
} else {
    Write-Host "[GTD Morning] 日次ログ既存（スキップ）: $logFile"
}

# ---- MANAOS morning API 呼び出し（port 5125）----
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:5125/api/morning" -Method POST -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[GTD Morning] morning API: OK"
} catch {
    Write-Host "[GTD Morning] morning API: スキップ（$($_.Exception.Message)）"
}

# ---- Pixel7 通知（GTD Capture Server 経由）----
# GTD Capture Server (port 5130) が Pixel7 から参照できるようにする
# Pixel7 は能動的に /api/gtd/morning/text を読む設計なので、
# ここでは Pixel7 の HTTP Gateway へ MacroDroid 通知を送る（optional）
$pixel7Host = if ($env:PIXEL7_HOST) { $env:PIXEL7_HOST } else { "100.84.2.125" }
$pixel7Url  = "http://${pixel7Host}:5122/api/macro/broadcast"
$pixel7Token= if ($env:PIXEL7_API_TOKEN) { $env:PIXEL7_API_TOKEN } else {
    $tf = "$root\.pixel7_api_token.txt"
    if (Test-Path $tf) { (Get-Content $tf -Raw).Trim() } else { "" }
}

$notifyBody = @{
    command = "Notify"
    extras  = @{
        title   = "GTD Morning - $Date"
        message = "Inbox:${inboxCount}件 / $(if($naItems.Count -gt 0){"Next:$($naItems.Count)件"} else {"Next Actions なし"})"
    }
} | ConvertTo-Json

if ($pixel7Token) {
    try {
        $headers = @{ Authorization = "Bearer $pixel7Token" }
        Invoke-RestMethod -Uri $pixel7Url -Method POST -Body $notifyBody `
            -ContentType "application/json" -Headers $headers -TimeoutSec 5 -ErrorAction Stop | Out-Null
        Write-Host "[GTD Morning] Pixel7通知: OK"
    } catch {
        Write-Host "[GTD Morning] Pixel7通知: スキップ（$($_.Exception.Message)）"
    }
} else {
    Write-Host "[GTD Morning] Pixel7通知: トークン未設定（スキップ）"
}

# ---- 通知本文を組み立て ----
$top3Lines = if ($naItems.Count -gt 0) {
    ($naItems | Select-Object -First 3 | ForEach-Object { "  • $($_.BaseName)" }) -join "`n"
} else { "  （Next Actions なし）" }
$inboxStatus = if ($inboxCount -ge 10) { "$inboxCount 件（要処理！）" } elseif ($inboxCount -gt 0) { "$inboxCount 件" } else { "クリア" }

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
            Write-Host "[GTD Morning] 通知: Slack OK"
            return
        } catch { Write-Host "[GTD Morning] Slack: NG ($($_.Exception.Message)) → ntfy にフォールバック" }
    }

    # 2) ntfy.sh フォールバック（アカウント不要・スマートフォンアプリ対応）
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
    headers={'Title': sys.argv[2].encode('utf-8').decode('ascii','replace'), 'Priority': 'default', 'Tags': 'sunrise', 'Content-Type': 'text/plain; charset=utf-8'}
)
urllib.request.urlopen(req, timeout=8)
print('ntfy OK')
" "$Body" "$Title" 2>&1 | ForEach-Object { Write-Host "[GTD Morning] ntfy: $_" }
    } catch { Write-Host "[GTD Morning] ntfy: NG ($($_.Exception.Message))" }
}

if ($Notify) {
    $title = "ManaOS Morning $Date"
    $body  = "Inbox: $inboxStatus`nTop3:`n$top3Lines`n`n[1つやらないことを決めよう]"
    Send-ManaOSNotify -Title $title -Body $body
}

# ── GTD日次ログを git commit ────────────────────────────────────────────────
Write-Host "[GTD Morning] GTD変更を git commit..."
$commitOut = & python "$PSScriptRoot\tools\manaosctl.py" gtd commit 2>&1
$commitOut | ForEach-Object { Write-Host "[GTD Morning] commit: $_" }

# ---- サマリ出力 ----
Write-Host ""
Write-Host "============================================"
Write-Host " GTD Morning Routine 完了 - $Date"
Write-Host "============================================"
Write-Host " 日次ログ : $logFile"
Write-Host " Inbox    : $inboxCount 件"
Write-Host " Next Act : $($naItems.Count) 件"
Write-Host "============================================"
