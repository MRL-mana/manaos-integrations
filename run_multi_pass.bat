@echo off
chcp 65001 >nul
set USE_LM_STUDIO=1
set MANA_OCR_USE_LARGE_MODEL=1
python excel_llm_multi_pass_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_MULTIPASS.xlsx --passes 3
pause
