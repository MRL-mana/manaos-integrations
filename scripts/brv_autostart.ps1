# brv autostart - Ollama + ByteRover プロバイダー自動復旧
# タスクスケジューラ（ログオン時）から実行される

$logFile = "$env:LOCALAPPDATA\brv\logs\autostart.log"
function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Log "=== brv_autostart 開始 ==="

# 1. Ollama が起動するまで最大60秒待機
$maxWait = 60
$elapsed = 0
while ($elapsed -lt $maxWait) {
    try {
        $resp = Invoke-WebRequest "http://127.0.0.1:11434" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Log "Ollama 起動確認 (${elapsed}秒後)"
            break
        }
    } catch {
        # Ollama 未起動 → 起動試行（初回のみ）
        if ($elapsed -eq 0) {
            Log "Ollama が起動していないため起動を試みます"
            Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
        }
        Start-Sleep 3
        $elapsed += 3
    }
}

if ($elapsed -ge $maxWait) {
    Log "ERROR: Ollama が${maxWait}秒以内に起動しませんでした"
    exit 1
}

# 2. brv providers の状態を確認して必要なら再接続
Start-Sleep 2  # daemon 起動待ち
try {
    $provJson = brv providers --format json 2>&1 | ConvertFrom-Json
    $active = $provJson.data.provider
    Log "現在のプロバイダー: $active"

    if ($active -ne "openai-compatible") {
        Log "openai-compatible に再接続します"
        brv providers connect openai-compatible `
            --base-url http://127.0.0.1:11434/v1 `
            --api-key "ollama" `
            --model "mistral:latest" 2>&1 | ForEach-Object { Log $_ }
    } else {
        Log "プロバイダーは正常 ($active)"
    }
} catch {
    Log "WARNING: providers 確認失敗 → 再接続を試みます: $_"
    & brv providers connect openai-compatible `
        --base-url http://127.0.0.1:11434/v1 `
        --api-key "ollama" `
        --model "mistral:latest" 2>&1 | ForEach-Object { Log $_ }
}

Log "=== brv_autostart 完了 ==="
