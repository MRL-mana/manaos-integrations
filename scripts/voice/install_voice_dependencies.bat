@echo off
REM 音声機能統合の依存関係をインストール（Windows用）

echo 🎤 音声機能統合の依存関係をインストール中...
echo.

REM 基本パッケージ
echo [1/4] 基本パッケージをインストール中...
pip install faster-whisper
pip install openai-whisper
pip install websockets
pip install requests

echo.
echo [2/4] pyaudio をインストール中...
echo ⚠️  pyaudio はビルドが必要なため、以下のいずれかの方法を使用してください:
echo.
echo 方法1: condaを使用（推奨）
echo   conda install pyaudio
echo.
echo 方法2: ビルド済みwheelを使用
echo   https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio からダウンロード
echo   pip install PyAudio-*.whl
echo.
echo 方法3: Visual C++ Build Toolsをインストールしてから
echo   pip install pyaudio
echo.

echo [3/4] webrtcvad をインストール中...
echo ⚠️  webrtcvad はビルドが必要なため、以下のいずれかの方法を使用してください:
echo.
echo 方法1: Visual C++ Build Toolsをインストールしてから
echo   pip install webrtcvad
echo.
echo 方法2: condaを使用
echo   conda install -c conda-forge webrtcvad
echo.

echo [4/4] インストール状況を確認中...
python scripts/voice/check_voice_integration.py

echo.
echo ✅ インストール完了！
echo.
echo 💡 注意: pyaudio と webrtcvad はオプションです。
echo    マイク入力が必要な場合のみインストールしてください。
echo.

pause
