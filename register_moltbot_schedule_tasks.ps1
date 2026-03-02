#!/usr/bin/env powershell
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    ManaOS Moltbot の定期自動実行タスクを Windows Task Scheduler に登録

.DESCRIPTION
    朝（08:00）・昼（12:00）・夜（20:00）の3つのスケジュール実行タスクを登録します
    各タスクは Downloads フォルダを自動整理します

.EXAMPLE
    .\register_moltbot_schedule_tasks.ps1
#>

param(
    [switch]$AdminRequired = $true,
    [string]$WorkspacePath = "c:\Users\mana4\Desktop\manaos_integrations"
)

# Administrator権限チェック
function Test-AdminPrivilege {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($AdminRequired -and -not (Test-AdminPrivilege)) {
    Write-Host "⚠️  このスクリプトは Administrator 権限が必要です" -ForegroundColor Yellow
    Write-Host "   右クリック → [PowerShell で実行] で実行してください" -ForegroundColor Yellow
    exit 1
}

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  📅 ManaOS Moltbot スケジュール実行タスク登録            ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# タスク定義
$tasks = @(
    @{
        Name = "ManaOS_Moltbot_Morning_08"
        Time = "08:00:00"
        Description = "朝の自動整理 - Downloads を PDF/画像/その他に分類"
        DisplayName = "🌅 ManaOS: 朝の Downloads 整理"
    },
    @{
        Name = "ManaOS_Moltbot_Noon_12"
        Time = "12:00:00"
        Description = "昼の自動整理 - Download ファイル一覧取得・分類"
        DisplayName = "🌤️  ManaOS: 昼の Downloads 確認"
    },
    @{
        Name = "ManaOS_Moltbot_Evening_20"
        Time = "20:00:00"
        Description = "夜の自動整理 - Downloads を整理して完全にクリーンアップ"
        DisplayName = "🌙 ManaOS: 夜の Downloads 整理"
    }
)

$scriptBlock = @"
# Moltbot 自動実行スクリプト
`$WorkspacePath = "$WorkspacePath"
cd `$WorkspacePath

# 環境変数を設定
`$env:EXECUTOR='moltbot'
`$env:MOLTBOT_CLI_PATH='C:\Users\mana4\AppData\Roaming\npm\openclaw'
`$env:MOLTBOT_GATEWAY_DATA_DIR='`$WorkspacePath\moltbot_gateway_data'
`$env:PYTHONPATH=`$WorkspacePath

# ログファイル
`$logFile = "`$WorkspacePath\logs\moltbot_schedule_`$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
New-Item -ItemType Directory -Path (Split-Path `$logFile) -Force -ErrorAction SilentlyContinue | Out-Null

# 実行
try {
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Moltbot 計画実行開始" | Tee-Object -FilePath `$logFile -Append
    python -m manaos_moltbot_runner organize_downloads | Tee-Object -FilePath `$logFile -Append
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Moltbot 計画実行完了" | Tee-Object -FilePath `$logFile -Append
} catch {
    "`$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - エラー: `$_" | Tee-Object -FilePath `$logFile -Append
    exit 1
}
"@

$scriptPath = Join-Path $WorkspacePath "moltbot_scheduled_task.ps1"
$scriptBlock | Out-File -FilePath $scriptPath -Encoding UTF8
Write-Host "✅ スクリプト作成: $scriptPath" -ForegroundColor Green
Write-Host ""

# 各タスクを登録
foreach ($task in $tasks) {
    Write-Host "📋 タスク登録: $($task.DisplayName)" -ForegroundColor Yellow
    
    # 既存タスクを削除
    $existingTask = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "   既存タスクを削除中..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName $task.Name -Confirm:$false -ErrorAction SilentlyContinue
    }
    
    # トリガー設定
    $trigger = New-ScheduledTaskTrigger -Daily -At $task.Time
    
    # アクション設定
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`"" `
        -WorkingDirectory $WorkspacePath
    
    # 設定
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -RunWithoutNetwork $false `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable $true
    
    # プリンシパル（実行ユーザー）
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest
    
    # タスク登録
    try {
        Register-ScheduledTask `
            -TaskName $task.Name `
            -TaskPath "\ManaOS\" `
            -Trigger $trigger `
            -Action $action `
            -Settings $settings `
            -Principal $principal `
            -Description $task.Description `
            -Force | Out-Null
        
        Write-Host "   ✅ 登録成功: $($task.Time)" -ForegroundColor Green
        Write-Host "      タスク名: $($task.Name)" -ForegroundColor Gray
    } catch {
        Write-Host "   ❌ 登録失敗: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ スケジュール登録完了！                              ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📅 登録されたタスク:" -ForegroundColor Cyan
Write-Host "  🌅 朝 08:00 - Downloads 整理" -ForegroundColor Gray
Write-Host "  🌤️  昼 12:00 - Downloads 確認" -ForegroundColor Gray
Write-Host "  🌙 夜 20:00 - Downloads 最終整理" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 確認方法:" -ForegroundColor Cyan
Write-Host "  1. Windows タスク スケジューラを開く" -ForegroundColor Gray
Write-Host "  2. [タスク スケジューラ ライブラリ] → [ManaOS] を展開" -ForegroundColor Gray
Write-Host "  3. 上記3つのタスクが登録されていることを確認" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 ログファイル:" -ForegroundColor Cyan
Write-Host "  $WorkspacePath\logs\moltbot_schedule_YYYY-MM-DD_HH-MM-SS.log" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  注意: このスクリプトを実行するには Administrator 権限が必要です" -ForegroundColor Yellow
