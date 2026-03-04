# GTD Capture Server 起動スクリプト（バックグラウンド）
param([int]$Port = 5130)

$scriptPath = "C:\Users\mana4\Desktop\manaos_integrations\gtd_capture_server.py"
$pidFile    = "C:\Users\mana4\Desktop\manaos_integrations\.gtd_capture_server.pid"

# 既存プロセス確認
if (Test-Path $pidFile) {
    $oldProcId = Get-Content $pidFile -Raw | ForEach-Object { $_.Trim() }
    if ($oldProcId -and (Get-Process -Id $oldProcId -ErrorAction SilentlyContinue)) {
        Write-Host "[GTD Capture] 既に起動中 (PID=$oldProcId, port=$Port)"
        exit 0
    }
}

$env:GTD_CAPTURE_PORT = $Port

$proc = Start-Process python -ArgumentList $scriptPath `
    -RedirectStandardOutput "C:\Users\mana4\Desktop\manaos_integrations\logs\gtd_capture_server.log" `
    -RedirectStandardError  "C:\Users\mana4\Desktop\manaos_integrations\logs\gtd_capture_server.err" `
    -PassThru -WindowStyle Hidden

$proc.Id | Set-Content $pidFile -Encoding ASCII
Write-Host "[GTD Capture] 起動しました (PID=$($proc.Id), port=$Port)"
Write-Host "  endpoint: http://0.0.0.0:$Port/api/gtd/capture"
Write-Host "  health  : http://127.0.0.1:$Port/health"

# 起動確認（最大5秒待機）
$ok = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 -ErrorAction Stop
        if ($r.status -eq "ok") { $ok = $true; break }
    } catch {}
}
if ($ok) { Write-Host "[GTD Capture] ✅ ヘルスチェック OK" }
else     { Write-Host "[GTD Capture] ⚠️ ヘルスチェック失敗（ログ確認: logs/gtd_capture_server.log）" }
