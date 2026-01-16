# ComfyUIをエンコーディング修正付きで起動

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"

Write-Host "============================================================"
Write-Host "ComfyUI起動（エンコーディング修正付き）"
Write-Host "============================================================"
Write-Host ""
Write-Host "環境変数を設定しました:"
Write-Host "  PYTHONIOENCODING = $env:PYTHONIOENCODING"
Write-Host "  PYTHONLEGACYWINDOWSSTDIO = $env:PYTHONLEGACYWINDOWSSTDIO"
Write-Host ""
Write-Host "ComfyUIを起動します..."
Write-Host ""

$comfyuiPath = "C:\ComfyUI"
if (Test-Path $comfyuiPath) {
    Set-Location $comfyuiPath
    python main.py
} else {
    Write-Host "エラー: ComfyUIディレクトリが見つかりません: $comfyuiPath"
    Write-Host "ComfyUIのパスを確認してください。"
}
