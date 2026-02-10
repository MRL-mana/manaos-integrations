@echo off
REM Evaluate v1.1.1 (v1.1 + Layer2 LoRA). Run after run_layer2_lora_train.bat
set MODEL=D:\castle_ex_training\castle_ex_v1_1
set LORA=D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1
set EVAL_DATA=castle_ex_dataset_v1_1_eval.jsonl
set OUTPUT=evaluation_v1_1_1_layer2_lora.json

python castle_ex\castle_ex_evaluator_fixed.py ^
  --model %MODEL% ^
  --lora %LORA% ^
  --model-type transformers --prompt-format phi3 ^
  --eval-data %EVAL_DATA% ^
  --output %OUTPUT%

echo.
echo Check %OUTPUT% and use "v1.1 evaluation summary" for final judgment.
pause
