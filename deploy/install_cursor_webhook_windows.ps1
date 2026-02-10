Param(
    [string]$PythonPath = "C:\\Python311\\python.exe",
    [string]$ServiceName = "ManaOS_CursorWebhook",
    [string]$ScriptPath = "${PWD}\\manaos_integrations\\cursor_webhook.py",
    [string]$DisplayName = "ManaOS Cursor Webhook Service"
)

Write-Host "Installing Windows service: $ServiceName" -ForegroundColor Cyan

if (-not (Test-Path $PythonPath)) {
    Write-Host "[WARN] Python not found at $PythonPath. Specify correct path with -PythonPath." -ForegroundColor Yellow
}

$bin = "`"$PythonPath`" `"$ScriptPath`""

try {
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Write-Host "Service $ServiceName already exists. Stopping and removing..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 1
    }

    New-Service -Name $ServiceName -BinaryPathName $bin -DisplayName $DisplayName -StartupType Automatic
    Start-Service -Name $ServiceName
    Write-Host "[OK] Service installed and started." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to install service: $_" -ForegroundColor Red
    exit 1
}

Write-Host "To view logs, use the Windows Event Viewer or run the script manually for stdout logs." -ForegroundColor Gray
