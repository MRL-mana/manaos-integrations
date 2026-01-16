# LTX-2モデルとGemmaモデルのインストールスクリプト
# ComfyUIにLTX-2モデルとGemma 3 Text Encoderをインストール

param(
    [string]$ComfyUIPath = "",
    [switch]$SkipLTX2,
    [switch]$SkipGemma,
    [switch]$UseHuggingFaceCLI = $true
)

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "LTX-2モデルとGemmaモデルのインストール" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# ComfyUIパスの検索
if ([string]::IsNullOrEmpty($ComfyUIPath)) {
    Write-Host "[1] ComfyUIのインストール場所を検索中..." -ForegroundColor Yellow
    
    $searchPaths = @(
        "C:\ComfyUI",
        "$env:USERPROFILE\ComfyUI",
        "$env:USERPROFILE\Desktop\ComfyUI",
        "D:\ComfyUI",
        "E:\ComfyUI",
        "$env:USERPROFILE\Documents\ComfyUI"
    )
    
    $foundPath = $null
    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $mainPy = Join-Path $path "main.py"
            if (Test-Path $mainPy) {
                $foundPath = $path
                Write-Host "   ✅ 見つかりました: $foundPath" -ForegroundColor Green
                break
            }
        }
    }
    
    if ($null -eq $foundPath) {
        Write-Host "   ❌ ComfyUIが見つかりませんでした" -ForegroundColor Red
        Write-Host ""
        Write-Host "ComfyUIをインストールしてください:" -ForegroundColor Yellow
        Write-Host "  またはパスを指定してください:" -ForegroundColor Yellow
        Write-Host "  .\install_ltx2_models.ps1 -ComfyUIPath `"C:\path\to\ComfyUI`"" -ForegroundColor Yellow
        exit 1
    }
    
    $ComfyUIPath = $foundPath
} else {
    if (-not (Test-Path $ComfyUIPath)) {
        Write-Host "❌ 指定されたパスが存在しません: $ComfyUIPath" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[2] ディレクトリ構造を確認中..." -ForegroundColor Yellow

# ディレクトリの作成
$checkpointsPath = Join-Path $ComfyUIPath "models\checkpoints"
$textEncodersPath = Join-Path $ComfyUIPath "models\text_encoders"
$ltxVideoPath = Join-Path $checkpointsPath "LTX-Video"

if (-not (Test-Path $checkpointsPath)) {
    New-Item -Path $checkpointsPath -ItemType Directory -Force | Out-Null
    Write-Host "   ✅ 作成: $checkpointsPath" -ForegroundColor Green
}

if (-not (Test-Path $textEncodersPath)) {
    New-Item -Path $textEncodersPath -ItemType Directory -Force | Out-Null
    Write-Host "   ✅ 作成: $textEncodersPath" -ForegroundColor Green
}

if (-not (Test-Path $ltxVideoPath)) {
    New-Item -Path $ltxVideoPath -ItemType Directory -Force | Out-Null
    Write-Host "   ✅ 作成: $ltxVideoPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3] LTX-2モデルの確認..." -ForegroundColor Yellow

if (-not $SkipLTX2) {
    $ltx2Model = Get-ChildItem -Path $checkpointsPath -Filter "*ltx-2-19b-distilled*.safetensors" -ErrorAction SilentlyContinue
    if ($ltx2Model) {
        Write-Host "   ✅ LTX-2モデルが見つかりました: $($ltx2Model.Name)" -ForegroundColor Green
        Write-Host "      サイズ: $([math]::Round($ltx2Model.Length / 1GB, 2)) GB" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  LTX-2モデルが見つかりません" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   LTX-2 19B Distilledモデルをダウンロードしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq "Y" -or $response -eq "y") {
            Write-Host ""
            Write-Host "   [3-1] Hugging Face CLIの確認..." -ForegroundColor Yellow
            
            if ($UseHuggingFaceCLI) {
                # Hugging Face CLIを使用
                $hfCliInstalled = Get-Command "huggingface-cli" -ErrorAction SilentlyContinue
                if ($hfCliInstalled) {
                    Write-Host "   ✅ Hugging Face CLIが見つかりました" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "   [3-2] LTX-2モデルをダウンロード中..." -ForegroundColor Yellow
                    Write-Host "   これには時間がかかる場合があります（約40GB）..." -ForegroundColor Gray
                    
                    Push-Location $ComfyUIPath
                    try {
                        $downloadCmd = "huggingface-cli download Lightricks/LTX-2 --include `"ltx-2-19b-distilled.safetensors`" --local-dir `"$ltxVideoPath`""
                        Write-Host "   実行コマンド: $downloadCmd" -ForegroundColor Gray
                        Invoke-Expression $downloadCmd
                        
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host "   ✅ LTX-2モデルのダウンロードが完了しました" -ForegroundColor Green
                        } else {
                            Write-Host "   ❌ ダウンロードに失敗しました" -ForegroundColor Red
                            Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
                            Write-Host "   https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
                        }
                    } finally {
                        Pop-Location
                    }
                } else {
                    Write-Host "   ⚠️  Hugging Face CLIが見つかりません" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "   Hugging Face CLIをインストールするには:" -ForegroundColor Yellow
                    Write-Host "   pip install huggingface_hub[cli]" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "   または、手動でダウンロードしてください:" -ForegroundColor Yellow
                    Write-Host "   https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
                    Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                    Write-Host "   $checkpointsPath" -ForegroundColor Cyan
                }
            } else {
                Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
                Write-Host "   https://huggingface.co/Lightricks/LTX-2" -ForegroundColor Cyan
                Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                Write-Host "   $checkpointsPath" -ForegroundColor Cyan
            }
        }
    }
} else {
    Write-Host "   ⏭️  LTX-2モデルの確認をスキップしました" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[4] Gemma 3 Text Encoderモデルの確認..." -ForegroundColor Yellow

if (-not $SkipGemma) {
    $gemmaModel = Get-ChildItem -Path $textEncodersPath -Recurse -Filter "*gemma*3*12b*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gemmaModel) {
        Write-Host "   ✅ Gemmaモデルが見つかりました: $($gemmaModel.Name)" -ForegroundColor Green
        Write-Host "      パス: $($gemmaModel.FullName)" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠️  Gemma 3 Text Encoderモデルが見つかりません" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Gemma 3-12B IT QAT Q4_0 Unquantizedモデルをダウンロードしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq "Y" -or $response -eq "y") {
            Write-Host ""
            Write-Host "   [4-1] Hugging Face CLIの確認..." -ForegroundColor Yellow
            
            if ($UseHuggingFaceCLI) {
                $hfCliInstalled = Get-Command "huggingface-cli" -ErrorAction SilentlyContinue
                if ($hfCliInstalled) {
                    Write-Host "   ✅ Hugging Face CLIが見つかりました" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "   [4-2] Gemmaモデルをダウンロード中..." -ForegroundColor Yellow
                    Write-Host "   これには時間がかかる場合があります..." -ForegroundColor Gray
                    
                    Push-Location $ComfyUIPath
                    try {
                        # Gemmaモデルのディレクトリを作成
                        $gemmaDir = Join-Path $textEncodersPath "gemma-3-12b-it-qat-q4_0-unquantized"
                        if (-not (Test-Path $gemmaDir)) {
                            New-Item -Path $gemmaDir -ItemType Directory -Force | Out-Null
                        }
                        
                        # Gemmaモデルをダウンロード
                        # 注意: 実際のリポジトリ名を確認する必要があります
                        Write-Host "   Gemmaモデルのダウンロード先を確認中..." -ForegroundColor Gray
                        Write-Host "   手動でダウンロードすることを推奨します:" -ForegroundColor Yellow
                        Write-Host "   https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
                        Write-Host "   または" -ForegroundColor Gray
                        Write-Host "   https://huggingface.co/chenly124/gemma-3-12b-it-qat-q4_0-unquantized" -ForegroundColor Cyan
                        Write-Host ""
                        Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                        Write-Host "   $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Cyan
                    } finally {
                        Pop-Location
                    }
                } else {
                    Write-Host "   ⚠️  Hugging Face CLIが見つかりません" -ForegroundColor Yellow
                    Write-Host ""
                    Write-Host "   Hugging Face CLIをインストールするには:" -ForegroundColor Yellow
                    Write-Host "   pip install huggingface_hub[cli]" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "   または、手動でダウンロードしてください:" -ForegroundColor Yellow
                    Write-Host "   https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
                    Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                    Write-Host "   $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Cyan
                }
            } else {
                Write-Host "   手動でダウンロードしてください:" -ForegroundColor Yellow
                Write-Host "   https://huggingface.co/google/gemma-3-12b-it" -ForegroundColor Cyan
                Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
                Write-Host "   $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Cyan
            }
        }
    }
} else {
    Write-Host "   ⏭️  Gemmaモデルの確認をスキップしました" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "✅ インストール確認完了！" -ForegroundColor Green
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. モデルが正しく配置されているか確認:" -ForegroundColor Yellow
Write-Host "   - LTX-2モデル: $checkpointsPath\ltx-2-19b-distilled.safetensors" -ForegroundColor Gray
Write-Host "   - Gemmaモデル: $textEncodersPath\gemma-3-12b-it-qat-q4_0-unquantized\" -ForegroundColor Gray
Write-Host ""
Write-Host "2. ComfyUIを再起動:" -ForegroundColor Yellow
Write-Host "   ComfyUIを再起動して、新しいモデルを認識させてください" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 動作確認:" -ForegroundColor Yellow
Write-Host "   python generate_mana_mufufu_ltx2_video.py" -ForegroundColor Gray
Write-Host ""
