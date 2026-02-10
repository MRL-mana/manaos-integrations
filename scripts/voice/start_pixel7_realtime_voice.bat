@echo off
REM Pixel 7 + 母艦 リアルタイム音声: WebSocket(8765) とクライアント配信(8766) を両方起動
set ROOT=%~dp0..\..
cd /d "%ROOT%"

echo [1/2] WebSocket 8765 を起動します...
start "Voice WebSocket 8765" cmd /k python voice_realtime_streaming.py

timeout /t 2 /nobreak >nul

echo [2/2] クライアント配信 8766 を起動します...
start "Voice Client 8766" cmd /k python scripts\voice\serve_voice_client.py

echo.
echo 起動しました。Pixel 7 のブラウザで http://^<母艦IP^>:8766 を開き、
echo WebSocket に ws://^<母艦IP^>:8765 を入力して「開始」してください。
pause
