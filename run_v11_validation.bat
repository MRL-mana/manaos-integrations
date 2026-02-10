@echo off
REM v1.1 検証ラン（品質ほぼ維持・速度1桁改善）
REM max_seq=1024, batch=1, max_steps=2000, save_steps=500
REM v1.0 から新規に 2000 step だけ回し、Layer2 跳ね判定用。
set TRAIN_DATA=castle_ex_dataset_v1_1_train.jsonl
set EVAL_DATA=castle_ex_dataset_v1_1_eval.jsonl
set OUTPUT_DIR=D:\castle_ex_training\castle_ex_v1_1_validation
set HF_HUB_DISABLE_PROGRESS_BARS=1
set TQDM_DISABLE=1

python castle_ex\train_castle_ex_full.py ^
  --model D:\castle_ex_training\castle_ex_v1_0 ^
  --output-dir %OUTPUT_DIR% ^
  --train-data %TRAIN_DATA% ^
  --eval-data %EVAL_DATA% ^
  --no-eval ^
  --learning-rate 1.0e-5 ^
  --max-length 1024 ^
  --batch-size 1 ^
  --save-steps 500 ^
  --save-total-limit 2 ^
  --max-steps 2000

echo.
echo 検証ラン完了。次: 評価して【v1.1 評価サマリ（貼り用）】を出してください。
echo   python castle_ex\castle_ex_evaluator_fixed.py --eval-data %EVAL_DATA% --model %OUTPUT_DIR%\checkpoint-2000 --model-type transformers --prompt-format phi3 --output evaluation_v1_1_validation.json
echo 詳細: castle_ex\v11_validation_guide.md
pause
