@echo off
set TQDM_DISABLE=1
if "%COMFYUI_BASE%"=="" set COMFYUI_BASE=C:\ComfyUI
if not exist "%COMFYUI_BASE%\main.py" (
    echo ComfyUI not found: %COMFYUI_BASE%
    pause
    exit /b 1
)
cd /d "%COMFYUI_BASE%"
echo ComfyUI starting - http://localhost:8188
echo Press Ctrl+C to stop.
python main.py --port 8188
pause
