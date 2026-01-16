# System3 External Learning Schedule Setup Script
# 毎日深夜（デフォルト: 03:00）に外部情報収集を実行

param(
    [string]$ScriptPath = "C:\Users\mana4\Desktop\manaos_integrations\system3_external_learning.py",
    [string]$PythonPath = "python",
    [string]$TaskName = "System3_External_Learning",
    [string]$ScheduleTime = "03:00"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "System3 External Learning Schedule Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# スクリプトパスの確認
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Script Path: $ScriptPath" -ForegroundColor Green
Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Green
Write-Host "Schedule Time: $ScheduleTime" -ForegroundColor Green
Write-Host ""

# 環境変数確認
$serpapiKey = $env:SERPAPI_KEY
$githubToken = $env:GITHUB_TOKEN

if ($serpapiKey) {
    Write-Host "SERPAPI_KEY: Set" -ForegroundColor Green
} else {
    Write-Host "SERPAPI_KEY: Not set (fallback search will be used)" -ForegroundColor Yellow
}

if ($githubToken) {
    Write-Host "GITHUB_TOKEN: Set" -ForegroundColor Green
} else {
    Write-Host "GITHUB_TOKEN: Not set (GitHub search will be skipped)" -ForegroundColor Yellow
}

Write-Host ""

# Pythonフルパス取得
$pythonFullPath = (Get-Command $PythonPath).Source
Write-Host "Python Full Path: $pythonFullPath" -ForegroundColor Gray
Write-Host ""

# 既存のタスクを削除（存在する場合）
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Existing task removed" -ForegroundColor Green
}

# タスクアクションを作成
$action = New-ScheduledTaskAction -Execute $pythonFullPath -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)

# タスクトリガーを作成（毎日指定時刻）
$trigger = New-ScheduledTaskTrigger -Daily -At $ScheduleTime

# タスク設定
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# タスクを登録
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "System3 External Learning Pipeline (Web + GitHub)" -Force | Out-Null
    Write-Host "Scheduled task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Run:" -ForegroundColor Cyan
    $nextRun = (Get-ScheduledTask -TaskName $TaskName).NextRunTime
    Write-Host "  $nextRun" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check command:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Delete command:" -ForegroundColor Cyan
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Note: Set SERPAPI_KEY and GITHUB_TOKEN environment variables for full functionality" -ForegroundColor Yellow
} catch {
    Write-Host "ERROR: Task registration failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
