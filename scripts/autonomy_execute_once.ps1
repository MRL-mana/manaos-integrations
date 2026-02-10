# Autonomy System: /api/execute を1回だけ呼ぶ（Runbook due + 自律タスク）
# 使い方: .\autonomy_execute_once.ps1
# 環境変数 AUTONOMY_URL で先を変更可能（既定: http://localhost:5124）

$baseUrl = if ($env:AUTONOMY_URL) { $env:AUTONOMY_URL.TrimEnd("/") } else { "http://localhost:5124" }
$uri = "$baseUrl/api/execute"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -TimeoutSec 120
    $runbookCount = $response.runbook_count
    $count = $response.count
    Write-Host "Runbook: $runbookCount 件実行 / 自律タスク: $count 件実行"
    if ($response.runbook_results) {
        $response.runbook_results | ForEach-Object { Write-Host "  - $($_.runbook_id): $($_.status)" }
    }
    exit 0
} catch {
    Write-Error "Autonomy execute 失敗: $_"
    exit 1
}
