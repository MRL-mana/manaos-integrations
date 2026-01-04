# manaOS Windows自動起動設定スクリプト
# 管理者権限で実行してください

param(
    [switch]$Remove  # 自動起動を削除する場合
)

$ErrorActionPreference = "Stop"

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ このスクリプトは管理者権限で実行する必要があります" -ForegroundColor Red
    Write-Host "PowerShellを「管理者として実行」してください" -ForegroundColor Yellow
    exit 1
}

# パス設定
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverScript = Join-Path $scriptDir "start_server_with_notification.py"
$pythonExe = (Get-Command python).Source
$taskName = "manaOS-API-Server"

Write-Host "=" * 60
Write-Host " manaOS Windows自動起動設定" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

if ($Remove) {
    # タスクを削除
    Write-Host "自動起動タスクを削除中..." -ForegroundColor Yellow
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            Write-Host "✅ 自動起動タスクを削除しました" -ForegroundColor Green
        } else {
            Write-Host "⚠️  タスクが見つかりませんでした" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ タスク削除エラー: $_" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# サーバースクリプトの存在確認
if (-not (Test-Path $serverScript)) {
    Write-Host "❌ サーバースクリプトが見つかりません: $serverScript" -ForegroundColor Red
    exit 1
}

# Pythonの存在確認
if (-not (Test-Path $pythonExe)) {
    Write-Host "❌ Pythonが見つかりません: $pythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "設定情報:" -ForegroundColor Cyan
Write-Host "  サーバースクリプト: $serverScript"
Write-Host "  Python: $pythonExe"
Write-Host "  タスク名: $taskName"
Write-Host ""

# 既存のタスクを削除（存在する場合）
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "既存のタスクを削除中..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# タスクアクションを作成
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$serverScript`"" -WorkingDirectory $scriptDir

# タスクトリガーを作成（ログオン時とシステム起動時）
$trigger1 = New-ScheduledTaskTrigger -AtLogOn
$trigger2 = New-ScheduledTaskTrigger -AtStartup

# タスク設定
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# タスクプリンシパル（実行ユーザー）
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# タスクを登録
Write-Host "自動起動タスクを登録中..." -ForegroundColor Yellow
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger @($trigger1, $trigger2) `
        -Settings $settings `
        -Principal $principal `
        -Description "manaOS統合APIサーバー自動起動" `
        | Out-Null
    
    Write-Host "✅ 自動起動タスクを登録しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "設定内容:" -ForegroundColor Cyan
    Write-Host "  - ログオン時に自動起動"
    Write-Host "  - システム起動時に自動起動"
    Write-Host "  - 失敗時は最大3回再試行（1分間隔）"
    Write-Host ""
    Write-Host "確認方法:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName '$taskName'"
    Write-Host ""
    Write-Host "削除方法:" -ForegroundColor Cyan
    Write-Host "  .\setup_windows_autostart.ps1 -Remove"
    Write-Host ""
    
} catch {
    Write-Host "❌ タスク登録エラー: $_" -ForegroundColor Red
    exit 1
}











