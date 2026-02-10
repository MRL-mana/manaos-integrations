# 監査ローテを「毎月1日 0:00」に実行するタスクを登録する
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\register_audit_rotate_monthly.ps1

$ErrorActionPreference = "Stop"
$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq "deploy") { Set-Location ..\.. }
$repoRoot = (Get-Location).Path
$rotateScript = Join-Path $repoRoot "moltbot_gateway\deploy\rotate_audit.ps1"
if (-not (Test-Path $rotateScript)) {
    Write-Host "Error: run from repo root so moltbot_gateway\deploy\rotate_audit.ps1 is found."
    exit 1
}

$taskName = "MoltbotAuditRotate"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$rotateScript`"" -WorkingDirectory $repoRoot
# 毎日 0:00 に実行（月1だと -Monthly が使えない環境があるため）
$trigger = New-ScheduledTaskTrigger -Daily -At 00:00
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "OK. タスク '$taskName' を登録しました。毎日 0:00 に監査ローテが実行されます。"
Write-Host "無効化: Disable-ScheduledTask -TaskName '$taskName'"
Write-Host "手動実行: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "削除: Unregister-ScheduledTask -TaskName '$taskName'"
