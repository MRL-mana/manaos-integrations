@echo off
cd /d "%~dp0"
echo 止めるまで画像生成を繰り返します。このウィンドウを閉じるか Ctrl+C で停止。
echo.
python -u run_generate_until_stopped.py
pause
