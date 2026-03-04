# GTD Morning Auto タスクスケジューラ登録
# 毎日 07:00 に gtd_morning_auto.ps1 を自動実行

param(
    [string]$Time = "07:00",
    [switch]$Unregister
)

$taskName   = "ManaOS_GTD_Morning_Auto"
$scriptPath = "C:\Users\mana4\Desktop\manaos_integrations\gtd_morning_auto.ps1"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[$taskName] 解除しました"
    exit 0
}

# 既存チェック
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[$taskName] 既に登録済み（上書き更新）"
}

$action  = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At $Time

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "ManaOS GTD: 毎朝 $Time に日次ログ作成・Inbox確認・Next Actionsピックアップを実行" `
    -Force | Out-Null

Write-Host "[$taskName] 登録完了 - 毎日 $Time 自動実行"
Write-Host "  スクリプト: $scriptPath"
Write-Host "  確認: Get-ScheduledTask -TaskName '$taskName' | Select-Object TaskName,State"
