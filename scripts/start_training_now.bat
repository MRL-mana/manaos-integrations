@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 学習開始（現在の環境で実行）
echo ============================================================
echo.

REM 環境確認
echo [1/4] 環境確認中...
python castle_ex\\train_castle_ex_full.py --check-only
if %errorlevel% neq 0 (
    echo [エラー] 環境確認に失敗しました
    pause
    exit /b 1
)
echo.

REM ベースモデルの確認
echo [2/4] ベースモデル確認
echo.
echo デフォルトモデル: microsoft/Phi-3-mini-4k-instruct
echo.
set /p MODEL_INPUT="使用するモデルを入力（Enterでデフォルト）: "
if "%MODEL_INPUT%"=="" (
    set MODEL_INPUT=microsoft/Phi-3-mini-4k-instruct
)
echo 使用モデル: %MODEL_INPUT%
echo.

REM 学習開始確認
echo [3/4] 学習開始確認
echo.
echo 学習設定:
echo   - エポック数: 25
echo   - バッチサイズ: 2
echo   - 学習率: 2.0e-5
echo   - 最大シーケンス長: 2048
echo.
set /p CONFIRM="学習を開始しますか？ (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo 学習をキャンセルしました
    pause
    exit /b 0
)
echo.

REM 学習開始
echo [4/4] 学習開始
echo ============================================================
python castle_ex\\train_castle_ex_full.py --model %MODEL_INPUT% --epochs 25 --batch-size 2 --learning-rate 2.0e-5

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] 学習完了
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
)

pause
