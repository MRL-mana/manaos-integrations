@echo off
REM Pixel 7 コンパニオンモード - 起動手順の案内
REM 統合API(9500) と音声WebSocket(8765) を起動し、Pixel 7 で /companion を開く

set ROOT=%~dp0..\..
cd /d "%ROOT%"

echo ============================================
echo  Pixel 7 コンパニオンモード 起動案内
echo ============================================
echo.
echo [前提]
echo  - 統合API (9500) が起動していること
echo  - Pixel 7 ADB ブリッジ (5122) が起動していること（TTS 用）
echo  - 音声モードを使う場合: voice_realtime_streaming.py (8765)
echo.
echo [起動手順]
echo 1. 統合API を起動（未起動の場合）
echo    python unified_api_server.py
echo.
echo 2. 音声入力を使う場合
echo    start_pixel7_realtime_voice.bat を実行（WebSocket 8765）
echo.
echo 3. Pixel 7 のブラウザで以下を開く
echo    http://^<母艦のIP^>:9502/companion
echo    例: http://192.168.1.5:9502/companion
echo    例: http://100.x.x.x:9502/companion (Tailscale)
echo.
echo [できること]
echo  - テキスト入力でLLMと会話
echo  - 応答を Pixel 7 のスピーカーで読み上げ（TTS）
echo  - マイクボタンで音声入力（「レミ」のあとに話しかける）
echo.
pause
