@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 学習開始
echo ============================================================
echo.

REM Axolotlを使用する場合
if exist "axolotl" (
    echo Axolotlで学習を開始します...
    axolotl train castle_ex\castle_ex_training_config.yaml
    goto :end
)

REM LLaMA-Factoryを使用する場合
if exist "llama-factory" (
    echo LLaMA-Factoryで学習を開始します...
    set "TRAIN_DATA=castle_ex_dataset_v1_0_train.jsonl"
    if exist "data\castle_ex_dataset_v1_0_train.jsonl" set "TRAIN_DATA=data\castle_ex_dataset_v1_0_train.jsonl"
    llama-factory train ^
        --model_name_or_path <ベースモデル> ^
        --dataset %TRAIN_DATA% ^
        --output_dir ./outputs/castle_ex_v1_0 ^
        --num_train_epochs 25
    goto :end
)

echo [エラー] 外部トレーナーが見つかりません。
echo AxolotlまたはLLaMA-Factoryをインストールしてください。

:end
pause
