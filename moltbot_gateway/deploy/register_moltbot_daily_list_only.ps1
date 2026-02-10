# Moltbot list_only を毎日指定時刻に自動実行するタスクを登録
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\register_moltbot_daily_list_only.ps1
# 時刻変更: $env:MOLTBOT_DAILY_TIME = "09:00" などで指定（デフォルト 08:00）

$ErrorActionPreference = "Stop"
$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq "deploy") { Set-Location ..\.. }
$repoRoot = (Get-Location).Path

$taskName = "MoltbotDailyListOnly"
$dailyTime = $env:MOLTBOT_DAILY_TIME
if (-not $dailyTime) { $dailyTime = "08:00" }

# python で list_only を実行（-WorkingDirectory でリポジトリルートがカレントになる）
$runnerPath = Join-Path $repoRoot "manaos_moltbot_runner.py"
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$runnerPath`" list_only" -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $dailyTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "OK. タスク '$taskName' を登録しました。毎日 $dailyTime に list_only が実行されます。"
Write-Host "時刻変更: 削除してから MOLTBOT_DAILY_TIME=09:00 を設定し、このスクリプトを再実行"
Write-Host "無効化: Disable-ScheduledTask -TaskName '$taskName'"
Write-Host "手動実行: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "削除: Unregister-ScheduledTask -TaskName '$taskName'"
