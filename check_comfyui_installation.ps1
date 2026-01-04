# ComfyUIインストール確認スクリプト

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ComfyUI インストール確認" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# 検索パス
$searchPaths = @(
    "C:\ComfyUI",
    "$env:USERPROFILE\ComfyUI",
    "$env:USERPROFILE\Desktop\ComfyUI",
    "D:\ComfyUI",
    "E:\ComfyUI",
    "$env:USERPROFILE\Documents\ComfyUI",
    "$env:USERPROFILE\OneDrive\Desktop\ComfyUI"
)

Write-Host "[1] ComfyUIのインストール場所を検索中..." -ForegroundColor Yellow
Write-Host ""

$found = $false
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        $mainPy = Join-Path $path "main.py"
        if (Test-Path $mainPy) {
            Write-Host "   ✅ 見つかりました: $path" -ForegroundColor Green
            Write-Host "      main.py: $mainPy" -ForegroundColor Gray
            
            # Pythonバージョン確認
            Write-Host ""
            Write-Host "[2] Python環境の確認..." -ForegroundColor Yellow
            $pythonVersion = python --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   ✅ Python: $pythonVersion" -ForegroundColor Green
            } else {
                Write-Host "   ❌ Pythonが見つかりません" -ForegroundColor Red
            }
            
            # 依存関係確認
            Write-Host ""
            Write-Host "[3] 依存関係の確認..." -ForegroundColor Yellow
            $requirementsPath = Join-Path $path "requirements.txt"
            if (Test-Path $requirementsPath) {
                Write-Host "   ✅ requirements.txt: 存在" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  requirements.txt: 見つかりません" -ForegroundColor Yellow
            }
            
            # GPU確認
            Write-Host ""
            Write-Host "[4] GPU環境の確認..." -ForegroundColor Yellow
            $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
            if ($nvidiaSmi) {
                Write-Host "   ✅ NVIDIA GPU: 検出されました" -ForegroundColor Green
                nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | ForEach-Object {
                    Write-Host "      $_" -ForegroundColor Gray
                }
            } else {
                Write-Host "   ⚠️  NVIDIA GPU: 検出されませんでした（CPUモードで動作）" -ForegroundColor Yellow
            }
            
            # PyTorch確認
            Write-Host ""
            Write-Host "[5] PyTorchの確認..." -ForegroundColor Yellow
            $torchCheck = python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   ✅ $torchCheck" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  PyTorch: インストールされていない可能性があります" -ForegroundColor Yellow
            }
            
            Write-Host ""
            Write-Host "=" -NoNewline
            Write-Host ("=" * 59) -ForegroundColor Cyan
            Write-Host "起動コマンド:" -ForegroundColor Cyan
            Write-Host "  cd `"$path`"" -ForegroundColor Yellow
            Write-Host "  python main.py --port 8188" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "または、起動スクリプトを使用:" -ForegroundColor Cyan
            Write-Host "  .\start_comfyui_local.ps1 -ComfyUIPath `"$path`"" -ForegroundColor Yellow
            Write-Host ""
            
            $found = $true
            break
        }
    }
}

if (-not $found) {
    Write-Host "   ❌ ComfyUIが見つかりませんでした" -ForegroundColor Red
    Write-Host ""
    Write-Host "インストール方法:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Gitからクローン:" -ForegroundColor Cyan
    Write-Host "   cd C:\" -ForegroundColor Gray
    Write-Host "   git clone https://github.com/comfyanonymous/ComfyUI.git" -ForegroundColor Gray
    Write-Host "   cd ComfyUI" -ForegroundColor Gray
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. または、リリース版をダウンロード:" -ForegroundColor Cyan
    Write-Host "   https://github.com/comfyanonymous/ComfyUI/releases" -ForegroundColor Gray
    Write-Host ""
}


















