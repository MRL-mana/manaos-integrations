@echo off
REM 秘書レミ完全体を起動（Windows用）

echo 🎤 秘書レミ完全体を起動中...
echo.

REM 環境変数の確認
if not defined VOICEVOX_URL (
    set VOICEVOX_URL=http://127.0.0.1:50021
)

if not defined VOICE_STT_MODEL (
    set VOICE_STT_MODEL=large-v3
)

if not defined VOICE_STT_DEVICE (
    set VOICE_STT_DEVICE=cuda
)

echo 📋 設定:
echo   VOICEVOX_URL=%VOICEVOX_URL%
echo   VOICE_STT_MODEL=%VOICE_STT_MODEL%
echo   VOICE_STT_DEVICE=%VOICE_STT_DEVICE%
echo.

REM Pythonスクリプトを実行
python voice_secretary_remi.py

pause
