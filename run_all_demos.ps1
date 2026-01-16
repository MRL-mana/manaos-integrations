# すべてのデモを実行するスクリプト

Write-Host "=" * 60
Write-Host "LLMルーティングシステム デモ実行"
Write-Host "=" * 60
Write-Host ""

# デモ1: 難易度分析デモ
Write-Host "[1] 難易度分析デモを実行..." -ForegroundColor Yellow
python demo_llm_routing.py

Write-Host ""
Write-Host "[2] パフォーマンス監視を実行しますか？ (y/n): " -ForegroundColor Yellow -NoNewline
$perfInput = Read-Host

if ($perfInput -eq "y") {
    Write-Host ""
    Write-Host "   パフォーマンス監視を実行中..." -ForegroundColor Yellow
    python monitor_llm_performance.py
}

Write-Host ""
Write-Host "=" * 60
Write-Host "すべてのデモが完了しました"
Write-Host "=" * 60
Write-Host ""



















