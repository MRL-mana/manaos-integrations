@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 完全学習開始
echo ============================================================
echo.

REM 環境確認
echo [1/3] 環境確認中...
python castle_ex\\train_castle_ex_full.py --check-only
if %errorlevel% neq 0 (
    echo [エラー] 環境確認に失敗しました
    pause
    exit /b 1
)
echo.

REM 学習開始
echo [2/3] 学習開始
echo ============================================================
echo.
echo 学習設定:
echo   - モデル: microsoft/Phi-3-mini-4k-instruct
echo   - エポック数: 25
echo   - バッチサイズ: 2
echo   - 学習率: 2.0e-5
echo   - 最大シーケンス長: 2048
echo.
echo 学習を開始します...
echo.

python castle_ex\\train_castle_ex_full.py --model microsoft/Phi-3-mini-4k-instruct --epochs 25 --batch-size 2 --learning-rate 2.0e-5 --max-length 2048

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [3/3] 学習完了
    echo ============================================================
    echo.
    echo 次のステップ:
    echo   1. 評価を実行:
    set "EVAL_DATA=castle_ex_dataset_v1_0_eval.jsonl"
    if exist "data\\castle_ex_dataset_v1_0_eval.jsonl" set "EVAL_DATA=data\\castle_ex_dataset_v1_0_eval.jsonl"
    echo      python castle_ex\\castle_ex_evaluator_fixed.py --eval-data %EVAL_DATA% --output evaluation_v1_0.json --model-type transformers --model ./outputs/castle_ex_v1_0
    echo.
) else (
    echo.
    echo [エラー] 学習中にエラーが発生しました
    echo.
    echo トラブルシューティング:
    echo   1. GPUメモリ不足の場合: --batch-size 1 に変更
    echo   2. メモリ不足の場合: --max-length 1024 に変更
    echo   3. エラーログを確認
    echo.
)

pause
