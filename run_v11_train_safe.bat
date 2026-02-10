@echo off
REM v1.1 training - stable mode (batch-size 1). Use if main run stops with CUDA illegal instruction.
set TRAIN_DATA=castle_ex_dataset_v1_1_train.jsonl
set EVAL_DATA=castle_ex_dataset_v1_1_eval.jsonl
set OUTPUT_DIR=D:\castle_ex_training\castle_ex_v1_1
set CHECKPOINT=D:\castle_ex_training\castle_ex_v1_0
set HF_HUB_DISABLE_PROGRESS_BARS=1
set TQDM_DISABLE=1
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
REM Sync CUDA ops for clearer errors (optional, slower)
REM set CUDA_LAUNCH_BLOCKING=1

python castle_ex\train_castle_ex_full.py ^
  --model D:\castle_ex_training\castle_ex_v1_0 ^
  --output-dir %OUTPUT_DIR% ^
  --train-data %TRAIN_DATA% ^
  --eval-data %EVAL_DATA% ^
  --resume-from-checkpoint auto ^
  --no-eval ^
  --learning-rate 1.0e-5 ^
  --save-steps 100 ^
  --save-total-limit 3 ^
  --batch-size 1

pause
