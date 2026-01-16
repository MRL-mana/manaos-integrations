@echo off
chcp 65001 >nul
echo ============================================================
echo LM Studio 全修正処理実行
echo ============================================================
echo.

set USE_LM_STUDIO=1
set MANA_OCR_USE_LARGE_MODEL=1

echo [1/3] 基本的なLLM修正
python excel_llm_ocr_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_LMSTUDIO.xlsx
echo.

echo [2/3] アンサンブル修正（複数モデル）
python excel_llm_ensemble_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ENSEMBLE_LMSTUDIO.xlsx
echo.

echo [3/3] 超強力修正（複数回のアンサンブル修正）
python excel_llm_ultra_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ULTRA_LMSTUDIO.xlsx --passes 3 --verbose
echo.

echo ============================================================
echo 全修正処理完了
echo ============================================================
pause
