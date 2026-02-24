param(
  [string]$TaskName = "ManaOS_DockerStack",
  [int]$UnifiedApiPort = 9502,
  [int]$LogTail = 40
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== ManaOS Docker Stack Autostart Status ===" -ForegroundColor Cyan
Write-Host "TaskName: $TaskName"

# Scheduled task
try {
  $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
  Write-Host "[TASK] present" -ForegroundColor Green
  [ordered]@{
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    UserId = $t.Principal.UserId
    LogonType = $t.Principal.LogonType
    RunLevel = $t.Principal.RunLevel
    ActionExecute = ($t.Actions | Select-Object -First 1).Execute
    ActionWorkingDirectory = ($t.Actions | Select-Object -First 1).WorkingDirectory
  } | ConvertTo-Json -Depth 5 | Write-Host
} catch {
  Write-Host "[TASK] absent" -ForegroundColor Yellow
  Write-Host $_.Exception.Message -ForegroundColor DarkGray
}

# Run-key fallback
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
try {
  $v = (Get-ItemProperty -Path $runKey -Name $TaskName -ErrorAction Stop).$TaskName
  Write-Host "[RUN] present" -ForegroundColor Yellow
  Write-Host $v
} catch {
  Write-Host "[RUN] absent" -ForegroundColor Green
}

# Watcher process
$wmi = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" |
  Where-Object { $_.CommandLine -like '*run_manaos_docker_stack_service.ps1*' } |
  Select-Object ProcessId, Name, CommandLine

if ($wmi) {
  Write-Host "[WATCHER] running" -ForegroundColor Green
  $wmi | ConvertTo-Json -Depth 4 | Write-Host
} else {
  Write-Host "[WATCHER] not found" -ForegroundColor Yellow
}

# Health
$healthUrl = "http://127.0.0.1:${UnifiedApiPort}/health"
try {
  $code = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 -Uri $healthUrl).StatusCode
  Write-Host "[HEALTH] $healthUrl => $code" -ForegroundColor Green
} catch {
  Write-Host "[HEALTH] $healthUrl => ERR: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Log tail
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$logFile = Join-Path $repoRoot "logs\manaos_docker_stack_watcher.log"
if (Test-Path $logFile) {
  Write-Host "[LOG] tail ${LogTail}: $logFile" -ForegroundColor Cyan
  Get-Content -Path $logFile -Tail $LogTail | ForEach-Object { $_ } 
} else {
  Write-Host "[LOG] not found: $logFile" -ForegroundColor Yellow
}
