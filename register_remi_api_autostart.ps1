# Register Remi API Auto-Start
# Preferred: Task Scheduler (may require admin depending on policy)
# Fallback: HKCU Run key (no admin)

$taskName = "Remi-API-AutoStart"
$scriptPath = Join-Path $PSScriptRoot "start_remi_api.ps1"
$psArgs = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""

function Register-WithTaskScheduler {
    # Remove existing task
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $psArgs `
        -WorkingDirectory $PSScriptRoot

    $trigger = New-ScheduledTaskTrigger -AtLogOn

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Auto-start Remi API (local_remi_api.py) on logon" `
        -Force `
        -ErrorAction Stop
}

function Register-WithRunKey {
    $runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $valueName = "RemiApiAutoStart"
    $cmd = "powershell.exe $psArgs"
    New-ItemProperty -Path $runKey -Name $valueName -Value $cmd -PropertyType String -Force | Out-Null
    return $valueName
}

try {
    Register-WithTaskScheduler
    Write-Host "" 
    Write-Host "Task '$taskName' registered successfully!" -ForegroundColor Green
    Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
    Write-Host "Remi API will auto-start on next logon." -ForegroundColor Cyan
} catch {
    Write-Host "" 
    Write-Host "Task Scheduler registration failed (likely needs admin)." -ForegroundColor Yellow
    Write-Host "Falling back to HKCU Run key auto-start (current user)." -ForegroundColor Yellow
    $name = Register-WithRunKey
    Write-Host "Run key '$name' registered successfully!" -ForegroundColor Green
    Write-Host "Remi API will auto-start on next logon." -ForegroundColor Cyan
}
