$ErrorActionPreference = "Stop"

$port = 5105
$baseDir = "C:\Users\mana4\Desktop\manaos_integrations"
$python = "C:\Users\mana4\AppData\Local\Programs\Python\Python310\python.exe"
$script = Join-Path $baseDir "mrl_memory_integration.py"

Set-Location $baseDir

try {
    $conn = Test-NetConnection -ComputerName "127.0.0.1" -Port $port -WarningAction SilentlyContinue
    if ($conn -and $conn.TcpTestSucceeded) {
        Write-Host "[OK] API already listening on port $port. Skip start."
        exit 0
    }
} catch {
    # ignore and attempt start
}

if (-not (Test-Path $python)) { throw "Python not found: $python" }
if (-not (Test-Path $script)) { throw "API script not found: $script" }

Write-Host "[INFO] Starting API server..."
Start-Process -FilePath $python -ArgumentList $script -WorkingDirectory $baseDir -WindowStyle Hidden
Start-Sleep -Seconds 2

try {
    $conn2 = Test-NetConnection -ComputerName "127.0.0.1" -Port $port -WarningAction SilentlyContinue
    if ($conn2 -and $conn2.TcpTestSucceeded) {
        Write-Host "[OK] API started (port $port is open)."
        exit 0
    }
} catch {
}

Write-Host "[WARN] API start attempted, but port $port not open yet."
exit 0

