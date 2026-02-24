@echo off
REM Layer2 LoRA training (v1.1 -> v1.1.1). See castle_ex/layer2_lora_recipe.md
set TRAIN_DATA=castle_ex_dataset_layer2_lora_train.jsonl
set EVAL_DATA=castle_ex_dataset_layer2_lora_eval.jsonl
set OUTPUT_DIR=D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1
set BASE_MODEL=D:\castle_ex_training\castle_ex_v1_1
set HF_HUB_DISABLE_PROGRESS_BARS=1
set TQDM_DISABLE=1
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
set PYTHONUNBUFFERED=1

python -u castle_ex\train_castle_ex_lora.py ^
  --base-model %BASE_MODEL% ^
  --train-data %TRAIN_DATA% ^
  --eval-data %EVAL_DATA% ^
  --output-dir %OUTPUT_DIR% ^
  --lora-r 16 --lora-alpha 32 --lora-dropout 0.05 ^
  --target-modules q_proj,k_proj,v_proj,o_proj ^
  --max-length 512 --batch-size 2 --gradient-accumulation-steps 8 ^
  --learning-rate 2e-4 --max-steps 2000 ^
  --save-steps 100 --eval-steps 500 --fp16

pause
