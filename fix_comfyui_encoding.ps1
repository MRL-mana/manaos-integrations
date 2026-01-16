# ComfyUIのエンコーディング問題を修正する環境変数設定

# 環境変数を設定
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"

Write-Host "環境変数を設定しました:"
Write-Host "  PYTHONIOENCODING = $env:PYTHONIOENCODING"
Write-Host "  PYTHONLEGACYWINDOWSSTDIO = $env:PYTHONLEGACYWINDOWSSTDIO"
Write-Host ""
Write-Host "ComfyUIを再起動してください。"
