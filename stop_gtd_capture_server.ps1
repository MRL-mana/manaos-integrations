# GTD Capture Server 停止スクリプト
$pidFile = "C:\Users\mana4\Desktop\manaos_integrations\.gtd_capture_server.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "[GTD Capture] PIDファイルなし（停止済みの可能性）"
    exit 0
}

$procId = Get-Content $pidFile -Raw | ForEach-Object { $_.Trim() }
if ($procId -and (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $procId -Force
    Write-Host "[GTD Capture] 停止しました (PID=$procId)"
} else {
    Write-Host "[GTD Capture] プロセス不在（既に停止済み）"
}
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
