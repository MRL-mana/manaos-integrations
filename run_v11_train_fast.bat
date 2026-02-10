@echo off
REM v1.1 追加学習「短縮版」: save_steps を 500 に上げて保存負荷を減らす。検証用なら max-steps で打ち切り可。
set TRAIN_DATA=castle_ex_dataset_v1_1_train.jsonl
set EVAL_DATA=castle_ex_dataset_v1_1_eval.jsonl
set OUTPUT_DIR=D:\castle_ex_training\castle_ex_v1_1
set HF_HUB_DISABLE_PROGRESS_BARS=1
set TQDM_DISABLE=1

REM 本番フル学習（25 epoch）だが保存は 500 step ごと → 約 9 回保存で済む
python castle_ex\train_castle_ex_full.py ^
  --model D:\castle_ex_training\castle_ex_v1_0 ^
  --output-dir %OUTPUT_DIR% ^
  --train-data %TRAIN_DATA% ^
  --eval-data %EVAL_DATA% ^
  --resume-from-checkpoint auto ^
  --no-eval ^
  --learning-rate 1.0e-5 ^
  --save-steps 500 ^
  --save-total-limit 3 ^
  --epochs 25

REM 検証だけしたい場合（約 2000 step で打ち切り）は上をコメントアウトして下を有効に
REM python castle_ex\train_castle_ex_full.py ^
REM   --model D:\castle_ex_training\castle_ex_v1_0 ^
REM   --output-dir %OUTPUT_DIR% ^
REM   --train-data %TRAIN_DATA% ^
REM   --eval-data %EVAL_DATA% ^
REM   --resume-from-checkpoint auto ^
REM   --no-eval ^
REM   --learning-rate 1.0e-5 ^
REM   --save-steps 500 ^
REM   --save-total-limit 2 ^
REM   --max-steps 2000

pause
