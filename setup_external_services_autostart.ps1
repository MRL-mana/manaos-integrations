# ManaOS External Services Auto-start Setup Script (Windows)
# n8n and Ollama auto-start configuration

Write-Host "ManaOS External Services Auto-start Setup..." -ForegroundColor Cyan

# Check administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Administrator privileges required. Please run as administrator." -ForegroundColor Yellow
    Write-Host "Right-click PowerShell > Run as administrator" -ForegroundColor Cyan
    exit 1
}

# n8n auto-start configuration
Write-Host "`n[1] n8n Auto-start Configuration..." -ForegroundColor Yellow

$n8nTaskName = "ManaOS_n8n"
$n8nTask = Get-ScheduledTask -TaskName $n8nTaskName -ErrorAction SilentlyContinue

if ($n8nTask) {
    Write-Host "  Removing existing task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $n8nTaskName -Confirm:$false
}

# Search for n8n path
$n8nPaths = @(
    "$env:APPDATA\npm\n8n.cmd",
    "$env:LOCALAPPDATA\npm\n8n.cmd",
    "C:\Program Files\nodejs\n8n.cmd",
    "$env:USERPROFILE\.n8n\n8n.cmd"
)

$n8nPath = $null
foreach ($path in $n8nPaths) {
    if (Test-Path $path) {
        $n8nPath = $path
        Write-Host "  n8n found: $n8nPath" -ForegroundColor Green
        break
    }
}

if ($null -eq $n8nPath) {
    # Use npx to start
    $n8nPath = "npx"
    $n8nArgs = "-y n8n start"
    Write-Host "  Using npx to start n8n" -ForegroundColor Yellow
} else {
    $n8nArgs = "start"
}

try {
    $n8nAction = New-ScheduledTaskAction -Execute $n8nPath -Argument $n8nArgs -WorkingDirectory $env:USERPROFILE
    $n8nTrigger = New-ScheduledTaskTrigger -AtStartup
    $n8nPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
    $n8nSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    Register-ScheduledTask -TaskName $n8nTaskName -Action $n8nAction -Trigger $n8nTrigger -Principal $n8nPrincipal -Settings $n8nSettings -Description "ManaOS n8n Auto-start" -ErrorAction Stop | Out-Null
    Write-Host "  [OK] n8n auto-start configuration completed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] n8n auto-start configuration failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Ollama auto-start configuration
Write-Host "`n[2] Ollama Auto-start Configuration..." -ForegroundColor Yellow

$ollamaTaskName = "ManaOS_Ollama"
$ollamaTask = Get-ScheduledTask -TaskName $ollamaTaskName -ErrorAction SilentlyContinue

if ($ollamaTask) {
    Write-Host "  Removing existing task..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $ollamaTaskName -Confirm:$false
}

# Search for Ollama path
$ollamaPaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "C:\Program Files\Ollama\ollama.exe",
    "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
)

$ollamaPath = $null
foreach ($path in $ollamaPaths) {
    if (Test-Path $path) {
        $ollamaPath = $path
        Write-Host "  Ollama found: $ollamaPath" -ForegroundColor Green
        break
    }
}

if ($null -eq $ollamaPath) {
    # Check if ollama command is in PATH
    $ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCheck) {
        $ollamaPath = "ollama"
        Write-Host "  ollama command found" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Ollama not found. Please configure manually." -ForegroundColor Yellow
        Write-Host "     Check Ollama installation path." -ForegroundColor Gray
    }
}

if ($null -ne $ollamaPath) {
    try {
        $ollamaAction = New-ScheduledTaskAction -Execute $ollamaPath -Argument "serve" -WorkingDirectory $env:USERPROFILE
        $ollamaTrigger = New-ScheduledTaskTrigger -AtStartup
        $ollamaPrincipal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
        # 常時起動設定: バッテリー時も起動、停止しない、再起動回数増加
        $ollamaSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Hours 0)
        
        Register-ScheduledTask -TaskName $ollamaTaskName -Action $ollamaAction -Trigger $ollamaTrigger -Principal $ollamaPrincipal -Settings $ollamaSettings -Description "ManaOS Ollama Always Running" -ErrorAction Stop | Out-Null
        Write-Host "  [OK] Ollama always-running configuration completed" -ForegroundColor Green
        Write-Host "     - Auto-start on system boot" -ForegroundColor Gray
        Write-Host "     - Auto-restart on failure (up to 10 times)" -ForegroundColor Gray
        Write-Host "     - Keep running even on battery" -ForegroundColor Gray
    } catch {
        Write-Host "  [WARN] Ollama auto-start configuration failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`nAuto-start configuration completed!" -ForegroundColor Green
Write-Host "`nTo verify configuration:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName ManaOS_*" -ForegroundColor Gray
Write-Host "`nTo disable auto-start:" -ForegroundColor Cyan
Write-Host "  Unregister-ScheduledTask -TaskName ManaOS_n8n -Confirm:`$false" -ForegroundColor Gray
Write-Host "  Unregister-ScheduledTask -TaskName ManaOS_Ollama -Confirm:`$false" -ForegroundColor Gray
