@echo off
REM webrtcvad インストールスクリプト（Windows用）

echo Installing webrtcvad...
echo.

echo ⚠️  webrtcvad は Windows でビルドが必要なパッケージです。
echo.
echo インストール方法:
echo.
echo 方法1: Visual C++ Build Tools をインストールしてから
echo   1. https://visualstudio.microsoft.com/visual-cpp-build-tools/ からダウンロード
echo   2. C++ ビルドツールをインストール
echo   3. pip install webrtcvad
echo.
echo 方法2: ビルド済みwheelを使用（推奨）
echo   https://www.lfd.uci.edu/~gohlke/pythonlibs/#webrtcvad からダウンロード
echo   pip install webrtcvad-*.whl
echo.
echo 方法3: condaを使用（condaが利用可能な場合）
echo   conda install -c conda-forge webrtcvad
echo.

echo 💡 注意: webrtcvad はオプションです。
echo   VAD改善機能が必要な場合のみインストールしてください。
echo   webrtcvadがなくても、基本的な音声機能は動作します。
echo.

pause
