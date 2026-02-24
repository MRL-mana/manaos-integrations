@echo off
REM v1.1.3: comparison救済特化データ生成（900/400/200）
cd /d %~dp0
py -3.10 castle_ex\generate_layer2_lora_data.py ^
  --out castle_ex_dataset_layer2_lora_v1_1_3.jsonl ^
  --n-comparison 900 ^
  --n-attribute 400 ^
  --n-part-whole 200 ^
  --split
if %errorlevel% neq 0 (
    echo [ERROR] v1.1.3データ生成失敗
    pause
    exit /b 1
)
echo.
echo [OK] v1.1.3データ生成完了:
echo   - castle_ex_dataset_layer2_lora_v1_1_3.jsonl （全1500件）
echo   - castle_ex_dataset_layer2_lora_train_v1_1_3.jsonl （学習用）
echo   - castle_ex_dataset_layer2_lora_eval_v1_1_3.jsonl （評価用）
pause
