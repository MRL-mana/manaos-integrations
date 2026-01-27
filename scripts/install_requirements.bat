@echo off
REM ManaOS 依存パッケージインストールスクリプト（バッチファイル）
REM 機能別に分割されたrequirementsファイルからインストール

setlocal enabledelayedexpansion

set PROFILE=all
if not "%1"=="" set PROFILE=%1

echo ========================================
echo ManaOS 依存パッケージインストール
echo ========================================
echo.

cd /d %~dp0\..

REM インストールするrequirementsファイルのリスト
if "%PROFILE%"=="all" (
    echo プロファイル: すべて（コア + 学習 + 音声 + ComfyUI）
    set REQUIREMENTS=requirements-core.txt requirements-training.txt requirements-voice.txt requirements-comfy.txt
) else if "%PROFILE%"=="core" (
    echo プロファイル: コアのみ
    set REQUIREMENTS=requirements-core.txt
) else if "%PROFILE%"=="training" (
    echo プロファイル: コア + 学習
    set REQUIREMENTS=requirements-core.txt requirements-training.txt
) else if "%PROFILE%"=="voice" (
    echo プロファイル: コア + 音声
    set REQUIREMENTS=requirements-core.txt requirements-voice.txt
) else if "%PROFILE%"=="comfy" (
    echo プロファイル: コア + ComfyUI
    set REQUIREMENTS=requirements-core.txt requirements-comfy.txt
) else if "%PROFILE%"=="dev" (
    echo プロファイル: コア + 開発環境
    set REQUIREMENTS=requirements-core.txt requirements-dev.txt
) else (
    echo [エラー] 不明なプロファイル: %PROFILE%
    echo 利用可能なプロファイル: all, core, training, voice, comfy, dev
    exit /b 1
)

echo.
echo [1/3] ファイル確認中...
for %%f in (%REQUIREMENTS%) do (
    if exist "%%f" (
        echo   [OK] %%f
    ) else (
        echo   [NG] %%f (見つかりません)
        exit /b 1
    )
)

echo.
echo [2/3] 依存パッケージをインストール中...
for %%f in (%REQUIREMENTS%) do (
    echo   インストール: %%f
    pip install -r "%%f"
    if errorlevel 1 (
        echo   [エラー] %%f のインストールに失敗しました
        exit /b 1
    )
)

echo.
echo [3/3] インストール確認中...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo   [警告] flask がインストールされていません
) else (
    echo   [OK] flask
)

pip show torch >nul 2>&1
if errorlevel 1 (
    echo   [警告] torch がインストールされていません
) else (
    echo   [OK] torch
)

echo.
echo ========================================
echo インストール完了
echo ========================================
echo.
echo 次のステップ:
echo   1. 環境変数を設定: scripts\setup_d_drive_env.bat
echo   2. テストを実行: python scripts\test_prompt_optimizer.py
echo   3. 学習チェック: python scripts\test_training_checks.py
echo.
pause
