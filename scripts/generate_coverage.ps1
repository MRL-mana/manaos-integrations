#!/usr/bin/env pwsh
# カバレッジレポート生成スクリプト（PowerShell版）

Write-Host "=" * 70
Write-Host "カバレッジレポート生成中..." -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host

# カバレッジの実行
python -m pytest tests/unit/ `
    --cov=. `
    --cov-config=.coveragerc `
    --cov-report=html `
    --cov-report=term-missing `
    --cov-report=xml `
    -v

if ($LASTEXITCODE -eq 0) {
    Write-Host
    Write-Host "=" * 70
    Write-Host "✅ カバレッジレポート生成完了" -ForegroundColor Green
    Write-Host "=" * 70
    Write-Host
    
    # HTML レポートなんど持ない場所を表示
    Write-Host "📊 HTML レポート: htmlcov/index.html" -ForegroundColor Yellow
    Write-Host "📄 XML レポート: coverage.xml" -ForegroundColor Yellow
    Write-Host
    
    # サマリーを表示
    Write-Host "カバレッジサマリー:" -ForegroundColor Cyan
    python -m coverage report --skip-covered
} else {
    Write-Host
    Write-Host "❌ カバレッジレポート生成失敗" -ForegroundColor Red
    exit 1
}
