# ComfyUIをエンコーディング修正付きで起動

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "1"
$env:PYTHONUTF8 = "1"

Write-Host "============================================================"
Write-Host "ComfyUI起動（エンコーディング修正付き）"
Write-Host "============================================================"
Write-Host ""
Write-Host "環境変数を設定しました:"
Write-Host "  PYTHONIOENCODING = $env:PYTHONIOENCODING"
Write-Host "  PYTHONLEGACYWINDOWSSTDIO = $env:PYTHONLEGACYWINDOWSSTDIO"
Write-Host "  PYTHONUTF8 = $env:PYTHONUTF8"
Write-Host ""
Write-Host "ComfyUIを起動します..."
Write-Host ""

$comfyuiPath = "C:\ComfyUI"
if (Test-Path $comfyuiPath) {
    Set-Location $comfyuiPath
    # 8188が既に使用中なら起動済みとみなす（重複起動によるErrno 10048を回避）
    try {
        $inUse = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue
    } catch {
        $inUse = $null
    }
    if ($inUse) {
        Write-Host "ComfyUIは既に起動しています: http://127.0.0.1:8188"
        Write-Host "（再起動したい場合は restart_comfyui_quick.bat を使ってください）"
    } else {
        python main.py
    }
} else {
    Write-Host "エラー: ComfyUIディレクトリが見つかりません: $comfyuiPath"
    Write-Host "ComfyUIのパスを確認してください。"
}
