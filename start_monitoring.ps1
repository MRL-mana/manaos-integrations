# LLMルーティングシステム 監視開始スクリプト

Write-Host "=" * 60
Write-Host "LLMルーティングシステム 監視開始"
Write-Host "=" * 60
Write-Host ""

Write-Host "監視モードを選択してください:" -ForegroundColor Cyan
Write-Host "  1. 監視ダッシュボード（リアルタイム表示）" -ForegroundColor White
Write-Host "  2. 自動再起動モニター（バックグラウンド実行）" -ForegroundColor White
Write-Host ""
Write-Host "選択 (1/2): " -ForegroundColor Yellow -NoNewline
$choice = Read-Host

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "監視ダッシュボードを起動します..." -ForegroundColor Yellow
    python llm_routing_monitor.py
} elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "自動再起動モニターを起動します..." -ForegroundColor Yellow
    Write-Host "（バックグラウンドで実行されます）" -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\auto_restart_services.ps1" -WindowStyle Minimized
    Write-Host "[OK] 自動再起動モニターを起動しました" -ForegroundColor Green
} else {
    Write-Host "無効な選択です" -ForegroundColor Red
}

Write-Host ""



















