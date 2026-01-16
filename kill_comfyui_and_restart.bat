@echo off
chcp 65001 >nul
echo ============================================================
echo ComfyUIを完全に終了して再起動します
echo ============================================================
echo.

echo [1/5] ポート8188を使用しているプロセスを確認中...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8188') do (
    echo     プロセスID: %%a を終了します
    taskkill /F /PID %%a >nul 2>&1
)
echo    完了
echo.

echo [2/5] 既存のComfyUIプロセスを終了中...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq ComfyUI*" >nul 2>&1
taskkill /F /IM python.exe /FI "COMMANDLINE eq *main.py*" >nul 2>&1
timeout /t 3 >nul
echo    完了
echo.

echo [3/5] ポートが解放されるまで待機中...
timeout /t 5 >nul
echo    完了
echo.

echo [4/5] ComfyUIディレクトリに移動...
cd /d C:\ComfyUI
if not exist main.py (
    echo    エラー: C:\ComfyUI\main.py が見つかりません
    pause
    exit /b 1
)
echo    完了
echo.

echo [5/5] ComfyUIを起動中...
start "ComfyUI" cmd /c "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && set PYTHONLEGACYWINDOWSSTDIO=1 && set PYTHONUTF8=1 && python main.py"
echo    完了
echo.

echo ============================================================
echo ComfyUIを起動しました
echo 数秒待ってから画像生成を再試行してください
echo ============================================================
timeout /t 10 >nul
