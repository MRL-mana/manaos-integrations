# Cursorプロンプト最適化ルール再有効化スクリプト
# プロンプト最適化の自動適用を再度有効化します

$rulesPath = "$env:USERPROFILE\Desktop\.cursor\rules\prompt-optimizer-rules.mdc"
$disabledPath = "$env:USERPROFILE\Desktop\.cursor\rules\prompt-optimizer-rules.mdc.disabled"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cursorプロンプト最適化ルール再有効化" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 無効化済みファイルの存在確認
if (Test-Path $disabledPath) {
    Write-Host "✓ 無効化済みファイルが見つかりました" -ForegroundColor Green
    Write-Host "  パス: $disabledPath" -ForegroundColor Gray
    Write-Host ""
    
    # 再有効化の確認
    Write-Host "プロンプト最適化ルールを再有効化しますか？" -ForegroundColor Yellow
    Write-Host "（これにより、プロンプト最適化による追加のLLM呼び出しが再開され、課金が増加する可能性があります）" -ForegroundColor Gray
    Write-Host ""
    $confirm = Read-Host "続行しますか？ (Y/N)"
    
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        try {
            # ファイルを再有効化（リネーム）
            Rename-Item -Path $disabledPath -NewName "prompt-optimizer-rules.mdc" -Force
            Write-Host ""
            Write-Host "✓ プロンプト最適化ルールを再有効化しました" -ForegroundColor Green
            Write-Host ""
            Write-Host "次のステップ:" -ForegroundColor Cyan
            Write-Host "1. Cursorを完全に再起動してください" -ForegroundColor White
            Write-Host "2. プロンプト最適化が自動的に適用されるようになります" -ForegroundColor White
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
    Write-Host "✗ 無効化済みファイルが見つかりませんでした" -ForegroundColor Red
    Write-Host "  パス: $disabledPath" -ForegroundColor Gray
    Write-Host ""
    
    # 既に有効化されているか確認
    if (Test-Path $rulesPath) {
        Write-Host "✓ プロンプト最適化ルールは既に有効化されています" -ForegroundColor Green
        Write-Host "  パス: $rulesPath" -ForegroundColor Gray
    }
    else {
        Write-Host "ファイルが存在しない可能性があります" -ForegroundColor Yellow
    }
    exit 0
}
