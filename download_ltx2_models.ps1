# LTX-2モデルとGemmaモデルの自動ダウンロードスクリプト
# Hugging Face CLIを使用してモデルをダウンロード

param(
    [string]$ComfyUIPath = "C:\ComfyUI",
    [switch]$SkipLTX2,
    [switch]$SkipGemma
)

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "LTX-2モデルとGemmaモデルの自動ダウンロード" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# ComfyUIパスの確認
if (-not (Test-Path $ComfyUIPath)) {
    Write-Host "❌ ComfyUIが見つかりません: $ComfyUIPath" -ForegroundColor Red
    exit 1
}

$mainPy = Join-Path $ComfyUIPath "main.py"
if (-not (Test-Path $mainPy)) {
    Write-Host "❌ main.pyが見つかりません: $ComfyUIPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ ComfyUIパス: $ComfyUIPath" -ForegroundColor Green
Write-Host ""

# Hugging Face CLIの確認
Write-Host "[1] Hugging Face CLIの確認..." -ForegroundColor Yellow
$hfCliInstalled = Get-Command "huggingface-cli" -ErrorAction SilentlyContinue
if (-not $hfCliInstalled) {
    Write-Host "   ⚠️  Hugging Face CLIが見つかりません" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Hugging Face CLIをインストールしますか？ (推奨)" -ForegroundColor Yellow
    Write-Host "   pip install huggingface_hub[cli]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   または、手動でダウンロードしてください:" -ForegroundColor Yellow
    Write-Host "   - LTX-2: https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
    Write-Host "   - Gemma: https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
    exit 1
}

Write-Host "   ✅ Hugging Face CLIが見つかりました" -ForegroundColor Green
Write-Host ""

# ディレクトリの作成
$checkpointsPath = Join-Path $ComfyUIPath "models\checkpoints"
$textEncodersPath = Join-Path $ComfyUIPath "models\text_encoders"
$ltxVideoPath = Join-Path $checkpointsPath "LTX-Video"

if (-not (Test-Path $checkpointsPath)) {
    New-Item -Path $checkpointsPath -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path $textEncodersPath)) {
    New-Item -Path $textEncodersPath -ItemType Directory -Force | Out-Null
}

if (-not (Test-Path $ltxVideoPath)) {
    New-Item -Path $ltxVideoPath -ItemType Directory -Force | Out-Null
}

# LTX-2モデルのダウンロード
if (-not $SkipLTX2) {
    Write-Host "[2] LTX-2モデルの確認..." -ForegroundColor Yellow
    $ltx2Model = Get-ChildItem -Path $checkpointsPath -Filter "*ltx-2-19b-distilled*.safetensors" -ErrorAction SilentlyContinue
    if ($ltx2Model) {
        Write-Host "   ✅ LTX-2モデルが見つかりました: $($ltx2Model.Name)" -ForegroundColor Green
        Write-Host "      サイズ: $([math]::Round($ltx2Model.Length / 1GB, 2)) GB" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  LTX-2モデルが見つかりません" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   [2-1] LTX-2 19B Distilledモデルをダウンロード中..." -ForegroundColor Yellow
        Write-Host "   これには時間がかかる場合があります（約40GB）..." -ForegroundColor Gray
        Write-Host "   ダウンロード先: $ltxVideoPath" -ForegroundColor Gray
        Write-Host ""
        
        Push-Location $ComfyUIPath
        try {
            $downloadCmd = "huggingface-cli download Lightricks/LTX-2 --include `"ltx-2-19b-distilled.safetensors`" --local-dir `"$ltxVideoPath`""
            Write-Host "   実行コマンド: $downloadCmd" -ForegroundColor Gray
            Write-Host ""
            
            Invoke-Expression $downloadCmd
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "   ✅ LTX-2モデルのダウンロードが完了しました" -ForegroundColor Green
                
                # ダウンロードされたファイルを確認
                $downloadedModel = Get-ChildItem -Path $ltxVideoPath -Filter "*ltx-2-19b-distilled*.safetensors" -ErrorAction SilentlyContinue
                if ($downloadedModel) {
                    Write-Host "   ファイル: $($downloadedModel.FullName)" -ForegroundColor Gray
                    Write-Host "   サイズ: $([math]::Round($downloadedModel.Length / 1GB, 2)) GB" -ForegroundColor Gray
                }
            } else {
                Write-Host ""
                Write-Host "   ❌ ダウンロードに失敗しました" -ForegroundColor Red
                Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
                Write-Host "   https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
                Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                Write-Host "   $checkpointsPath" -ForegroundColor Cyan
            }
        } catch {
            Write-Host ""
            Write-Host "   ❌ エラーが発生しました: $_" -ForegroundColor Red
            Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
            Write-Host "   https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
        } finally {
            Pop-Location
        }
    }
} else {
    Write-Host "[2] ⏭️  LTX-2モデルのダウンロードをスキップしました" -ForegroundColor Gray
}

Write-Host ""

# Gemmaモデルのダウンロード
if (-not $SkipGemma) {
    Write-Host "[3] Gemma 3 Text Encoderモデルの確認..." -ForegroundColor Yellow
    $gemmaModel = Get-ChildItem -Path $textEncodersPath -Recurse -Filter "*gemma*3*12b*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gemmaModel) {
        Write-Host "   ✅ Gemmaモデルが見つかりました: $($gemmaModel.Name)" -ForegroundColor Green
        Write-Host "      パス: $($gemmaModel.FullName)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  Gemma 3 Text Encoderモデルが見つかりません" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   [3-1] Gemma 3-12B ITモデルをダウンロード中..." -ForegroundColor Yellow
        Write-Host "   これには時間がかかる場合があります..." -ForegroundColor Gray
        Write-Host "   ダウンロード先: $textEncodersPath" -ForegroundColor Gray
        Write-Host ""
        
        Push-Location $ComfyUIPath
        try {
            # Gemmaモデルのディレクトリを作成
            $gemmaDir = Join-Path $textEncodersPath "gemma-3-12b-it-qat-q4_0-unquantized"
            if (-not (Test-Path $gemmaDir)) {
                New-Item -Path $gemmaDir -ItemType Directory -Force | Out-Null
            }
            
            # Gemmaモデルをダウンロード
            # 注意: 実際のリポジトリ構造に応じて調整が必要な場合があります
            Write-Host "   Gemmaモデルのダウンロード..." -ForegroundColor Gray
            Write-Host "   リポジトリ: google/gemma-3-12b-it" -ForegroundColor Gray
            Write-Host ""
            
            $downloadCmd = "huggingface-cli download google/gemma-3-12b-it --local-dir `"$gemmaDir`""
            Write-Host "   実行コマンド: $downloadCmd" -ForegroundColor Gray
            Write-Host ""
            
            Invoke-Expression $downloadCmd
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "   ✅ Gemmaモデルのダウンロードが完了しました" -ForegroundColor Green
            } else {
                Write-Host ""
                Write-Host "   ⚠️  ダウンロードに失敗した可能性があります" -ForegroundColor Yellow
                Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
                Write-Host "   https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
                Write-Host "   または" -ForegroundColor Gray
                Write-Host "   https://huggingface.co/chenly124/gemma-3-12b-it-qat-q4_0-unquantized" -ForegroundColor Cyan
                Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                Write-Host "   $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Cyan
            }
        } catch {
            Write-Host ""
            Write-Host "   ❌ エラーが発生しました: $_" -ForegroundColor Red
            Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
            Write-Host "   https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
        } finally {
            Pop-Location
        }
    }
} else {
    Write-Host "[3] ⏭️  Gemmaモデルのダウンロードをスキップしました" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "✅ ダウンロード処理完了！" -ForegroundColor Green
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. モデルが正しく配置されているか確認:" -ForegroundColor Yellow
Write-Host "   - LTX-2モデル: $checkpointsPath\ltx-2-19b-distilled.safetensors" -ForegroundColor Gray
Write-Host "   または: $ltxVideoPath\ltx-2-19b-distilled.safetensors" -ForegroundColor Gray
Write-Host "   - Gemmaモデル: $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Gray
Write-Host ""
Write-Host "2. ComfyUIを再起動:" -ForegroundColor Yellow
Write-Host "   ComfyUIを再起動して、新しいモデルを認識させてください" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 動作確認:" -ForegroundColor Yellow
Write-Host "   python generate_mana_mufufu_ltx2_video.py" -ForegroundColor Gray
Write-Host ""
