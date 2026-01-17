@echo off
chcp 65001 >nul
echo ============================================================
echo LM Studio 全修正処理実行（ログ出力あり）
echo ============================================================
echo.

set USE_LM_STUDIO=1
set MANA_OCR_USE_LARGE_MODEL=1

echo [開始時刻] %date% %time%
echo.

echo [1/3] 基本的なLLM修正
echo ----------------------------------------
python excel_llm_ocr_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_LMSTUDIO.xlsx
if errorlevel 1 (
    echo [エラー] 基本的なLLM修正に失敗しました
    pause
    exit /b 1
)
echo [完了] 基本的なLLM修正が完了しました
echo.

echo [2/3] アンサンブル修正（複数モデル）
echo ----------------------------------------
python excel_llm_ensemble_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ENSEMBLE_LMSTUDIO.xlsx
if errorlevel 1 (
    echo [エラー] アンサンブル修正に失敗しました
    pause
    exit /b 1
)
echo [完了] アンサンブル修正が完了しました
echo.

echo [3/3] 超強力修正（複数回のアンサンブル修正）
echo ----------------------------------------
python excel_llm_ultra_corrector.py SKM_TEST_P1.xlsx SKM_TEST_P1_ULTRA_LMSTUDIO.xlsx --passes 3 --verbose
if errorlevel 1 (
    echo [エラー] 超強力修正に失敗しました
    pause
    exit /b 1
)
echo [完了] 超強力修正が完了しました
echo.

echo ============================================================
echo [終了時刻] %date% %time%
echo 全修正処理完了
echo ============================================================
pause
