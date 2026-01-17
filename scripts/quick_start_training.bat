@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 学習クイックスタート
echo ============================================================
echo.

REM 環境確認
echo [1/5] 環境確認中...
python --version
echo.

REM ファイル確認
echo [2/5] ファイル確認中...
set "TRAIN_DATA=castle_ex_dataset_v1_0_train.jsonl"
set "EVAL_DATA=castle_ex_dataset_v1_0_eval.jsonl"
if exist "data\castle_ex_dataset_v1_0_train.jsonl" set "TRAIN_DATA=data\castle_ex_dataset_v1_0_train.jsonl"
if exist "data\castle_ex_dataset_v1_0_eval.jsonl" set "EVAL_DATA=data\castle_ex_dataset_v1_0_eval.jsonl"

if not exist "%TRAIN_DATA%" (
    echo [エラー] 訓練データが見つかりません: %TRAIN_DATA%
    pause
    exit /b 1
)
if not exist "castle_ex\\castle_ex_schedule_v1_0.json" (
    if not exist "castle_ex_schedule_v1_0.json" (
    echo [エラー] 学習スケジュールが見つかりません
    pause
    exit /b 1
    )
)
echo [OK] 必要なファイルが存在します
echo.

REM 外部トレーナー確認
echo [3/5] 外部トレーナー確認中...
where axolotl >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Axolotlが見つかりました
    echo.
    echo [4/5] 学習を開始します...
    axolotl train castle_ex\\castle_ex_training_config.yaml
    goto :eval
)

where llama-factory >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] LLaMA-Factoryが見つかりました
    echo.
    echo [4/5] 学習を開始します...
    echo [注意] ベースモデルを指定してください
    llama-factory train --model_name_or_path <ベースモデル> --dataset %TRAIN_DATA% --output_dir ./outputs/castle_ex_v1_0 --num_train_epochs 25
    goto :eval
)

echo [警告] 外部トレーナーが見つかりませんでした
echo.
echo インストールオプション:
echo   1. Axolotl: pip install axolotl
echo   2. LLaMA-Factory: git clone https://github.com/hiyouga/LLaMA-Factory.git
echo.
echo インストール後、このスクリプトを再実行してください。
pause
exit /b 1

:eval
echo.
echo ============================================================
echo [5/5] 学習完了後の評価
echo ============================================================
echo.
echo 学習完了後、以下のコマンドで評価を実行してください:
echo.
echo python castle_ex\\castle_ex_evaluator_fixed.py --eval-data %EVAL_DATA% --output evaluation_v1_0.json --model-type ollama --model ^<モデル名^>
echo.
pause
