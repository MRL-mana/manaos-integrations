@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 学習開始（低メモリ設定）
echo ============================================================
echo.
echo VRAM節約のための設定:
echo   - バッチサイズ: 1
echo   - 最大シーケンス長: 1024
echo   - Gradient Accumulation: 4（実効バッチサイズ: 4）
echo   - Gradient Checkpointing: 有効
echo.

python castle_ex\train_castle_ex_full.py --model microsoft/Phi-3-mini-4k-instruct --epochs 25 --batch-size 1 --learning-rate 2.0e-5 --max-length 1024

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] 学習完了
    echo ============================================================
) else (
    echo.
    echo [エラー] 学習中にエラーが発生しました
    echo.
    echo さらにメモリを節約する場合:
    echo   - バッチサイズを確認（既に1）
    echo   - 最大シーケンス長を512に減らす
    echo   - エラーログを確認
    echo.
)

pause
