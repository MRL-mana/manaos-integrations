@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ============================================================
echo Optimized correction with cache
echo ============================================================
echo.

set USE_LM_STUDIO=1
set MANA_OCR_USE_LARGE_MODEL=1
set MANA_ENSEMBLE_MAX_MODELS=1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set LOG=optimized_correction.log
echo Log: %CD%\%LOG%
echo.

echo Running optimized correction...
python -u "%~dp0\excel\optimize_correction_pipeline.py" "%~dp0\..\SKM_TEST_P1.xlsx" "%~dp0\..\SKM_TEST_P1_OPTIMIZED.xlsx" --verbose > "%LOG%" 2>&1
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
