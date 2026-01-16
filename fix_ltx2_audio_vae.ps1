# LTX-2 audio_vaeモジュールエラー修正スクリプト

Write-Host "=" * 60
Write-Host "LTX-2 audio_vaeモジュールエラー修正"
Write-Host "=" * 60
Write-Host ""

$latentsFile = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\latents.py"

if (-not (Test-Path $latentsFile)) {
    Write-Host "[NG] latents.pyが見つかりません: $latentsFile" -ForegroundColor Red
    exit 1
}

Write-Host "[1] latents.pyのバックアップを作成..." -ForegroundColor Yellow
$backupFile = "$latentsFile.backup"
Copy-Item -Path $latentsFile -Destination $backupFile -Force
Write-Host "   [OK] バックアップを作成しました: $backupFile" -ForegroundColor Green

Write-Host ""
Write-Host "[2] latents.pyを修正..." -ForegroundColor Yellow

# 修正内容を確認
$content = Get-Content -Path $latentsFile -Raw -Encoding UTF8

if ($content -match "from comfy\.ldm\.lightricks\.vae\.audio_vae import LATENT_DOWNSAMPLE_FACTOR") {
    Write-Host "   [INFO] 修正が必要です" -ForegroundColor Gray
    
    # 修正を適用
    $replacement = @"
# 一時的な回避策: audio_vaeモジュールが見つからない場合の代替
try:
    from comfy.ldm.lightricks.vae.audio_vae import LATENT_DOWNSAMPLE_FACTOR
except ImportError:
    # audio_vaeモジュールが見つからない場合のデフォルト値
    # 通常、LTX-2のオーディオVAEのダウンサンプルファクターは8
    LATENT_DOWNSAMPLE_FACTOR = 8
"@
    $newContent = $content -replace 'from comfy\.ldm\.lightricks\.vae\.audio_vae import LATENT_DOWNSAMPLE_FACTOR', $replacement
    
    Set-Content -Path $latentsFile -Value $newContent -Encoding UTF8 -NoNewline
    Write-Host "   [OK] latents.pyを修正しました" -ForegroundColor Green
} else {
    Write-Host "   [INFO] 既に修正済みです" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[3] 修正内容を確認..." -ForegroundColor Yellow
$checkContent = Get-Content -Path $latentsFile -Raw -Encoding UTF8
if ($checkContent -match "LATENT_DOWNSAMPLE_FACTOR = 8") {
    Write-Host "   [OK] 修正が正しく適用されました" -ForegroundColor Green
} else {
    Write-Host "   [WARN] 修正が適用されていない可能性があります" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 60
Write-Host "修正完了"
Write-Host "=" * 60
Write-Host ""
Write-Host "次のステップ:"
Write-Host "1. ComfyUIを再起動してください"
Write-Host "2. ノードが正しく読み込まれたか確認: python check_comfyui_nodes.py"
Write-Host "3. 動画生成を再度試行: python generate_mana_mufufu_ltx2_video.py"
