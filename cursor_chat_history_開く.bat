@echo off
cd /d "%~dp0"

echo ========================================
echo   Cursor チャット履歴を開く
echo ========================================
echo.

REM Python を探す（py 優先、次に python）
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY (
  echo [エラー] Python が見つかりません。
  echo.
  goto :finish
)

echo 履歴を読み込んでいます...
%PY% cursor_chat_history_to_html.py
if errorlevel 1 (
  echo.
  echo [エラー] 読み込みに失敗しました。
  goto :finish
)

if exist "%~dp0cursor_chat_history.html" (
  echo ブラウザで開きます...
  start "" "%~dp0cursor_chat_history.html"
  echo 完了しました。
) else (
  echo [エラー] cursor_chat_history.html が作成されませんでした。
)

:finish
echo.
pause
