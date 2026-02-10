# デバイス状態を定期確認するタスクを登録（例: 30分ごと）
# 管理者で実行するとタスクスケジューラに登録されます
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir "..")
$checkScript = Join-Path $root "scripts\check_devices_online.ps1"
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "devices_health_$(Get-Date -Format 'yyyyMMdd').log"

$taskName = "ManaOS_Devices_Health_Check"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$checkScript`" | Tee-Object -FilePath `"$logFile`" -Append" `
    -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

try {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Set-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
        Write-Host "[OK] タスクを更新しました: $taskName（30分ごとにデバイス確認）" -ForegroundColor Green
    } else {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
        Write-Host "[OK] タスクを登録しました: $taskName（30分ごとにデバイス確認）" -ForegroundColor Green
    }
    Write-Host "ログ: $logFile" -ForegroundColor Gray
} catch {
    Write-Host "[INFO] タスク登録には管理者権限が必要な場合があります。" -ForegroundColor Yellow
    Write-Host "手動で確認: .\scripts\check_devices_online.ps1" -ForegroundColor Gray
}
Write-Host "解除: Unregister-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
