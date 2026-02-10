# 母艦で Gateway を「ログオン時」に自動起動するタスクを登録する
# 使い方: リポジトリルートで .\moltbot_gateway\deploy\register_gateway_autostart.ps1

$ErrorActionPreference = "Stop"
$here = (Get-Location).Path
if ((Split-Path -Leaf $here) -eq "deploy") { Set-Location ..\.. }
$repoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $repoRoot "moltbot_gateway\gateway_app.py"))) {
    Write-Host "Error: run from repo root so moltbot_gateway is found."
    exit 1
}

$taskName = "MoltbotGateway"
$wrapperPath = Join-Path $repoRoot "moltbot_gateway\deploy\run_gateway_wrapper_production.ps1"
if (-not (Test-Path $wrapperPath)) {
    Write-Host "Error: run_gateway_wrapper_production.ps1 not found."
    exit 1
}
# 常駐タスクは production ラッパーを実行（gateway_production.env があれば本物、なければモック）

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`"" -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "OK. タスク '$taskName' を登録しました。ログオン時に Gateway が起動します。"
Write-Host "本物運用: moltbot_gateway\deploy\gateway_production.env を作成し EXECUTOR=moltbot と MOLTBOT_DAEMON_* を設定すると本物 OpenClaw に接続します。"
Write-Host "無効化: Disable-ScheduledTask -TaskName '$taskName'"
Write-Host "手動実行: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "削除: Unregister-ScheduledTask -TaskName '$taskName'"
