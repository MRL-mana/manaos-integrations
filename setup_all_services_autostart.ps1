# manaOS全サービス自動起動設定スクリプト
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
$pythonExe = (Get-Command python).Source

Write-Host "=" * 60
Write-Host " manaOS全サービス自動起動設定" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

# サービス定義
$services = @(
    @{
        Name = "manaOS-API-Server"
        Script = "start_server_with_notification.py"
        Description = "manaOS統合APIサーバー"
        Priority = "必須"
    },
    @{
        Name = "manaOS-Realtime-Dashboard"
        Script = "realtime_dashboard.py"
        Description = "リアルタイムダッシュボード"
        Priority = "推奨"
    },
    @{
        Name = "manaOS-Master-Control"
        Script = "master_control.py"
        Description = "マスターコントロールパネル"
        Priority = "推奨"
    }
)

if ($Remove) {
    # すべてのタスクを削除
    Write-Host "自動起動タスクを削除中..." -ForegroundColor Yellow
    foreach ($service in $services) {
        $taskName = $service.Name
        try {
            $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($task) {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
                Write-Host "✅ $taskName を削除しました" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️  $taskName の削除に失敗: $_" -ForegroundColor Yellow
        }
    }
    exit 0
}

# 各サービスを設定
foreach ($service in $services) {
    $taskName = $service.Name
    $scriptFile = Join-Path $scriptDir $service.Script
    $description = $service.Description
    $priority = $service.Priority
    
    Write-Host "設定中: $description ($priority)" -ForegroundColor Cyan
    
    # スクリプトの存在確認
    if (-not (Test-Path $scriptFile)) {
        Write-Host "  ⚠️  スクリプトが見つかりません: $scriptFile" -ForegroundColor Yellow
        Write-Host "  → スキップします" -ForegroundColor Gray
        Write-Host ""
        continue
    }
    
    # 既存のタスクを削除（存在する場合）
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "  既存のタスクを削除中..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    
    # タスクアクションを作成
    $action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptFile`"" -WorkingDirectory $scriptDir
    
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
    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger @($trigger1, $trigger2) `
            -Settings $settings `
            -Principal $principal `
            -Description $description `
            | Out-Null
        
        Write-Host "  ✅ 自動起動タスクを登録しました" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ タスク登録エラー: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "=" * 60
Write-Host "設定完了" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "設定されたサービス:" -ForegroundColor Cyan
foreach ($service in $services) {
    $scriptFile = Join-Path $scriptDir $service.Script
    if (Test-Path $scriptFile) {
        Write-Host "  ✅ $($service.Description) ($($service.Priority))" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $($service.Description) (スクリプト未発見)" -ForegroundColor Yellow
    }
}
Write-Host ""
Write-Host "確認方法:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName 'manaOS-*'"
Write-Host ""
Write-Host "削除方法:" -ForegroundColor Cyan
Write-Host "  .\setup_all_services_autostart.ps1 -Remove"
Write-Host ""











