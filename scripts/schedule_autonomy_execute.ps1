# Autonomy System: 指定間隔で /api/execute を繰り返し呼ぶ（Runbook + 自律タスク）
# 使い方: .\schedule_autonomy_execute.ps1 [-IntervalMinutes 10]
# 終了: Ctrl+C

param(
    [int] $IntervalMinutes = 10
)

$baseUrl = if ($env:AUTONOMY_URL) { $env:AUTONOMY_URL.TrimEnd("/") } else { "http://127.0.0.1:5124" }
$uri = "$baseUrl/api/execute"

Write-Host "Autonomy 定期実行を開始します。間隔: $IntervalMinutes 分。停止は Ctrl+C。"

while ($true) {
    $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -TimeoutSec 120
        Write-Host "[$now] Runbook: $($response.runbook_count) / タスク: $($response.count)"
    } catch {
        Write-Warning "[$now] 実行失敗: $_"
    }
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
