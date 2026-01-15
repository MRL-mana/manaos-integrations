# ComfyUI起動スクリプト（SVI × Wan 2.2用）

param(
    [int]$Port = 8188,
    [switch]$Background
)

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "ComfyUI 起動スクリプト（SVI × Wan 2.2用）" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

$ComfyUIPath = "C:\ComfyUI"

# ComfyUIの確認
if (-not (Test-Path $ComfyUIPath)) {
    Write-Host "[NG] ComfyUIが見つかりません: $ComfyUIPath" -ForegroundColor Red
    Write-Host "ComfyUIをインストールしてください:" -ForegroundColor Yellow
    Write-Host "  .\install_comfyui.ps1" -ForegroundColor Cyan
    exit 1
}

# ポート使用状況確認
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[INFO] ポート $Port は既に使用中です" -ForegroundColor Yellow
    Write-Host "ComfyUIは既に起動している可能性があります" -ForegroundColor Gray
    Write-Host ""
    Write-Host "ブラウザで http://localhost:$Port にアクセスしてください" -ForegroundColor Cyan
    exit 0
}

Write-Host "[INFO] ComfyUIを起動します..." -ForegroundColor Yellow
Write-Host "  パス: $ComfyUIPath" -ForegroundColor Gray
Write-Host "  ポート: $Port" -ForegroundColor Gray
Write-Host ""

if ($Background) {
    Write-Host "[INFO] バックグラウンドで起動します" -ForegroundColor Yellow
    Start-Process python -ArgumentList "main.py", "--port", $Port.ToString() -WorkingDirectory $ComfyUIPath -WindowStyle Hidden
    Write-Host "[OK] ComfyUIをバックグラウンドで起動しました" -ForegroundColor Green
    Write-Host ""
    Write-Host "ブラウザで http://localhost:$Port にアクセスしてください" -ForegroundColor Cyan
} else {
    Write-Host "ComfyUIサーバーを起動中..." -ForegroundColor Green
    Write-Host "ブラウザで http://localhost:$Port にアクセスしてください" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "停止する場合は Ctrl+C を押してください" -ForegroundColor Yellow
    Write-Host ""

    Push-Location $ComfyUIPath
    try {
        python main.py --port $Port
    } finally {
        Pop-Location
    }
}
