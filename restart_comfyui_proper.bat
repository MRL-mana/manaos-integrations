@echo off
chcp 65001 >nul
echo ============================================================
echo ComfyUIを完全に再起動します
echo ============================================================
echo.

echo [1/4] 既存のComfyUIプロセスを終了中...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ComfyUI*" >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE eq *main.py*" >nul 2>&1
timeout /t 3 >nul
echo    完了
echo.

echo [2/4] 環境変数を設定...
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1
set PYTHONUTF8=1
echo    完了
echo.

echo [3/4] ComfyUIディレクトリに移動...
cd /d C:\ComfyUI
if not exist main.py (
    echo    エラー: C:\ComfyUI\main.py が見つかりません
    pause
    exit /b 1
)
set COMFY_PYTHON=python
if exist C:\ComfyUI\.venv\Scripts\python.exe (
    set COMFY_PYTHON=C:\ComfyUI\.venv\Scripts\python.exe
)
echo    完了
echo.

echo [4/4] ComfyUIを起動中...
start "ComfyUI" cmd /c "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && set PYTHONLEGACYWINDOWSSTDIO=1 && set PYTHONUTF8=1 && \"%COMFY_PYTHON%\" main.py --port 8188"
echo    完了
echo.

echo ============================================================
echo ComfyUIを起動しました
echo 数秒待ってから画像生成を再試行してください
echo ============================================================
timeout /t 5 >nul
