# LLMルーティングシステム ログビューアー

Write-Host "=" * 60
Write-Host "LLMルーティングシステム ログビューアー"
Write-Host "=" * 60
Write-Host ""

$logDir = "logs"

if (-not (Test-Path $logDir)) {
    Write-Host "[警告] ログディレクトリが存在しません" -ForegroundColor Yellow
    exit 1
}

Write-Host "ログファイル一覧:" -ForegroundColor Cyan
$logFiles = Get-ChildItem -Path $logDir -Filter "*.jsonl" | Sort-Object LastWriteTime -Descending

if ($logFiles) {
    foreach ($file in $logFiles) {
        $lineCount = (Get-Content $file.FullName | Measure-Object -Line).Lines
        Write-Host "  - $($file.Name): $lineCount 行" -ForegroundColor Gray
    }
} else {
    Write-Host "  ログファイルが見つかりません" -ForegroundColor Yellow
}

Write-Host ""

Write-Host "表示するログを選択してください:" -ForegroundColor Cyan
Write-Host "  1. リクエストログ" -ForegroundColor White
Write-Host "  2. エラーログ" -ForegroundColor White
Write-Host "  3. パフォーマンスログ" -ForegroundColor White
Write-Host "  4. すべて" -ForegroundColor White
Write-Host ""
Write-Host "選択 (1-4): " -ForegroundColor Yellow -NoNewline
$choice = Read-Host

$selectedFiles = @()
switch ($choice) {
    "1" { $selectedFiles = @("llm_routing_requests.jsonl") }
    "2" { $selectedFiles = @("llm_routing_errors.jsonl") }
    "3" { $selectedFiles = @("llm_routing_performance.jsonl") }
    "4" { $selectedFiles = @("llm_routing_requests.jsonl", "llm_routing_errors.jsonl", "llm_routing_performance.jsonl") }
    default {
        Write-Host "無効な選択です" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "表示する行数 (デフォルト: 20): " -ForegroundColor Yellow -NoNewline
$lineCount = Read-Host
$lineCount = if ($lineCount -match '^\d+$') { [int]$lineCount } else { 20 }

Write-Host ""
Write-Host "=" * 60
Write-Host "ログ表示"
Write-Host "=" * 60
Write-Host ""

foreach ($fileName in $selectedFiles) {
    $filePath = Join-Path $logDir $fileName
    if (Test-Path $filePath) {
        Write-Host "📄 $fileName" -ForegroundColor Cyan
        Write-Host "-" * 60
        
        $lines = Get-Content $filePath -Tail $lineCount
        foreach ($line in $lines) {
            try {
                $json = $line | ConvertFrom-Json
                $json | ConvertTo-Json -Depth 10 | Write-Host
            } catch {
                Write-Host $line
            }
            Write-Host ""
        }
        Write-Host ""
    }
}

Write-Host "=" * 60



















