@echo off
REM webrtcvad 簡単インストールスクリプト（Windows用）

echo ============================================================
echo webrtcvad インストール（VAD改善機能）
echo ============================================================
echo.

REM 既にインストールされているか確認
python -c "import webrtcvad; print('webrtcvad is already installed'); exit(0)" 2>nul
if %errorlevel% == 0 (
    echo OK: webrtcvad は既にインストールされています
    pause
    exit /b 0
)

echo webrtcvad が見つかりません。インストール方法を選択してください。
echo.
echo 【推奨】ビルド済みwheelを使用（最も簡単）:
echo   1. ブラウザで以下を開く:
echo      https://www.lfd.uci.edu/~gohlke/pythonlibs/#webrtcvad
echo   2. Python 3.10用のwheelファイルをダウンロード
echo      （ファイル名: webrtcvad-2.0.10-cp310-cp310-win_amd64.whl）
echo   3. ダウンロードしたwheelファイルをこのフォルダにコピー
echo   4. 以下のコマンドを実行:
echo      pip install webrtcvad-2.0.10-cp310-cp310-win_amd64.whl
echo.
echo 【代替】Visual C++ Build Toolsをインストール:
echo   1. https://visualstudio.microsoft.com/visual-cpp-build-tools/ からダウンロード
echo   2. C++ ビルドツールをインストール（数GB、時間がかかります）
echo   3. 新しいコマンドプロンプトを開く
echo   4. pip install webrtcvad
echo.
echo 【自動インストール】自動インストールスクリプトを実行:
echo   python scripts/voice/auto_install_webrtcvad.py
echo.

REM ダウンロードフォルダからwheelファイルを検索
echo ダウンロードフォルダからwheelファイルを検索中...
if exist "%USERPROFILE%\Downloads\webrtcvad-*.whl" (
    echo wheelファイルが見つかりました！
    for %%f in ("%USERPROFILE%\Downloads\webrtcvad-*.whl") do (
        echo インストール中: %%f
        pip install "%%f"
        if %errorlevel% == 0 (
            echo OK: インストール成功！
            python -c "import webrtcvad; print('webrtcvad installed successfully')"
        ) else (
            echo NG: インストール失敗
        )
        goto :end
    )
) else (
    echo wheelファイルが見つかりませんでした
)

:end
echo.
echo 詳細な手順: docs/voice_webrtcvad_install_guide.md
echo.
pause
