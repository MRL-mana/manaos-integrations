# Cursorプロンプト最適化ルール無効化スクリプト
# 課金削減のため、プロンプト最適化の自動適用を無効化します

$rulesPath = "$env:USERPROFILE\Desktop\.cursor\rules\prompt-optimizer-rules.mdc"
$disabledPath = "$env:USERPROFILE\Desktop\.cursor\rules\prompt-optimizer-rules.mdc.disabled"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cursorプロンプト最適化ルール無効化" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ファイルの存在確認
if (Test-Path $rulesPath) {
    Write-Host "✓ プロンプト最適化ルールファイルが見つかりました" -ForegroundColor Green
    Write-Host "  パス: $rulesPath" -ForegroundColor Gray
    Write-Host ""
    
    # 既に無効化されているか確認
    if (Test-Path $disabledPath) {
        Write-Host "⚠ 既に無効化されています" -ForegroundColor Yellow
        Write-Host "  無効化済みファイル: $disabledPath" -ForegroundColor Gray
        Write-Host ""
        Write-Host "再度有効化する場合は、enable_prompt_optimizer.ps1 を実行してください" -ForegroundColor Yellow
        exit 0
    }
    
    # 無効化の確認
    Write-Host "プロンプト最適化ルールを無効化しますか？" -ForegroundColor Yellow
    Write-Host "（これにより、プロンプト最適化による追加のLLM呼び出しが停止し、課金が削減されます）" -ForegroundColor Gray
    Write-Host ""
    $confirm = Read-Host "続行しますか？ (Y/N)"
    
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        try {
            # ファイルを無効化（リネーム）
            Rename-Item -Path $rulesPath -NewName "prompt-optimizer-rules.mdc.disabled" -Force
            Write-Host ""
            Write-Host "✓ プロンプト最適化ルールを無効化しました" -ForegroundColor Green
            Write-Host ""
            Write-Host "次のステップ:" -ForegroundColor Cyan
            Write-Host "1. Cursorを完全に再起動してください" -ForegroundColor White
            Write-Host "2. Cursorのアカウント設定で使用量を確認してください" -ForegroundColor White
            Write-Host ""
            Write-Host "期待される効果: 約50%の課金削減" -ForegroundColor Green
        }
        catch {
            Write-Host ""
            Write-Host "✗ エラーが発生しました: $_" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host ""
        Write-Host "キャンセルされました" -ForegroundColor Yellow
        exit 0
    }
}
else {
    Write-Host "✗ プロンプト最適化ルールファイルが見つかりませんでした" -ForegroundColor Red
    Write-Host "  パス: $rulesPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "ファイルが存在しないか、既に無効化されている可能性があります" -ForegroundColor Yellow
    exit 1
}
