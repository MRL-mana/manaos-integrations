@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo ULTRA AGGRESSIVE correction (5 ensemble passes)
echo ============================================================
echo.

set USE_LM_STUDIO=1
set MANA_OCR_USE_LARGE_MODEL=1
set MANA_ENSEMBLE_MAX_MODELS=1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set LOG=ultra_aggressive.log
echo Log: %CD%\%LOG%
echo.

echo Running...
python -u "%~dp0excel_llm_ultra_aggressive_corrector.py" "%~dp0SKM_TEST_P1.xlsx" "%~dp0SKM_TEST_P1_ULTRA_AGGRESSIVE.xlsx" --passes 5 --verbose > "%LOG%" 2>&1
set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================================
echo Finished. ExitCode=%EXITCODE%
echo ============================================================
echo.
echo Tail of log:
powershell -NoProfile -Command "Get-Content -Path '%CD%\\%LOG%' -Tail 30 -ErrorAction SilentlyContinue"
echo.
pause
exit /b %EXITCODE%
