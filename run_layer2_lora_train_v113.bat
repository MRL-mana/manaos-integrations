@echo off
REM v1.1.3: 新LoRA学習（comparison固定、3000step）
echo ========================================
echo Layer2 LoRA v1.1.3 学習開始
echo - base: castle_ex_v1_1
echo - data: v1_1_3 (comparison 900件固定化)
echo - steps: 3000
echo - save/eval: 100
echo ========================================
cd /d %~dp0
set HF_HUB_DISABLE_PROGRESS_BARS=1
set TQDM_DISABLE=1
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
set PYTHONUNBUFFERED=1

python -u castle_ex\train_castle_ex_lora.py ^
  --base-model D:\castle_ex_training\castle_ex_v1_1 ^
  --train-data castle_ex_dataset_layer2_lora_v1_1_3_train.jsonl ^
  --eval-data castle_ex_dataset_layer2_lora_v1_1_3_eval.jsonl ^
  --output-dir D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3 ^
  --lora-r 16 ^
  --lora-alpha 32 ^
  --lora-dropout 0.05 ^
  --target-modules q_proj,k_proj,v_proj,o_proj ^
  --max-length 512 ^
  --batch-size 2 ^
  --gradient-accumulation-steps 8 ^
  --learning-rate 2e-4 ^
  --max-steps 3000 ^
  --save-steps 500 ^
  --eval-steps 500 ^
  --fp16

if %errorlevel% neq 0 (
    echo [ERROR] 学習失敗
    pause
    exit /b 1
)
echo.
echo [OK] v1.1.3学習完了: D:\castle_ex_training\lora_castle_ex_layer2_v1_1_3
pause
