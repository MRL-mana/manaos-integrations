# ComfyUI 自動インストールスクリプト（母艦用）

param(
    [string]$InstallPath = "C:\ComfyUI",
    [switch]$SkipDependencies,
    [switch]$CPUOnly
)

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ComfyUI 自動インストールスクリプト" -ForegroundColor Cyan
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# 管理者権限チェック（不要だが念のため）
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "⚠️  管理者権限で実行中です（通常は不要）" -ForegroundColor Yellow
}

# Python確認
Write-Host "[1] Python環境の確認..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Pythonがインストールされていません" -ForegroundColor Red
    Write-Host "   Python 3.8以上をインストールしてください:" -ForegroundColor Yellow
    Write-Host "   https://www.python.org/downloads/" -ForegroundColor Cyan
    exit 1
}
Write-Host "   ✅ $pythonVersion" -ForegroundColor Green

# Git確認
Write-Host ""
Write-Host "[2] Gitの確認..." -ForegroundColor Yellow
$gitVersion = git --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Gitがインストールされていません" -ForegroundColor Red
    Write-Host "   Gitをインストールしてください:" -ForegroundColor Yellow
    Write-Host "   https://git-scm.com/download/win" -ForegroundColor Cyan
    exit 1
}
Write-Host "   ✅ $gitVersion" -ForegroundColor Green

# インストール先の確認
Write-Host ""
Write-Host "[3] インストール先の確認..." -ForegroundColor Yellow
Write-Host "   パス: $InstallPath" -ForegroundColor Gray

if (Test-Path $InstallPath) {
    Write-Host "   ⚠️  既にディレクトリが存在します" -ForegroundColor Yellow
    $mainPy = Join-Path $InstallPath "main.py"
    if (Test-Path $mainPy) {
        Write-Host "   ✅ ComfyUIは既にインストールされています" -ForegroundColor Green
        Write-Host ""
        Write-Host "起動する場合は:" -ForegroundColor Cyan
        Write-Host "  .\start_comfyui_local.ps1 -ComfyUIPath `"$InstallPath`"" -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "   既存のディレクトリを削除しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq "Y" -or $response -eq "y") {
            Remove-Item -Path $InstallPath -Recurse -Force
            Write-Host "   削除しました" -ForegroundColor Green
        } else {
            Write-Host "   インストールをキャンセルしました" -ForegroundColor Yellow
            exit 0
        }
    }
}

# ディレクトリ作成
Write-Host ""
Write-Host "[4] ComfyUIをクローン中..." -ForegroundColor Yellow
try {
    $parentDir = Split-Path -Parent $InstallPath
    if (-not (Test-Path $parentDir)) {
        New-Item -Path $parentDir -ItemType Directory -Force | Out-Null
    }
    
    Write-Host "   Gitリポジトリをクローン中..." -ForegroundColor Gray
    git clone https://github.com/comfyanonymous/ComfyUI.git $InstallPath
    
    if ($LASTEXITCODE -ne 0) {
        throw "Gitクローンに失敗しました"
    }
    
    Write-Host "   ✅ クローン完了" -ForegroundColor Green
} catch {
    Write-Host "   ❌ エラー: $_" -ForegroundColor Red
    exit 1
}

# 依存関係のインストール
if (-not $SkipDependencies) {
    Write-Host ""
    Write-Host "[5] 依存関係をインストール中..." -ForegroundColor Yellow
    Write-Host "   これには数分かかる場合があります..." -ForegroundColor Gray
    
    Push-Location $InstallPath
    try {
        # PyTorchのインストール
        Write-Host "   PyTorchをインストール中..." -ForegroundColor Gray
        if ($CPUOnly) {
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        } else {
            # CUDA 12.1用（最新のGPU）
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   ⚠️  PyTorchのインストールに問題がありました" -ForegroundColor Yellow
            Write-Host "   手動でインストールしてください:" -ForegroundColor Yellow
            Write-Host "   pip install torch torchvision torchaudio" -ForegroundColor Cyan
        } else {
            Write-Host "   ✅ PyTorchインストール完了" -ForegroundColor Green
        }
        
        # requirements.txtのインストール
        Write-Host "   その他の依存関係をインストール中..." -ForegroundColor Gray
        if (Test-Path "requirements.txt") {
            pip install -r requirements.txt
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "   ⚠️  一部の依存関係のインストールに問題がありました" -ForegroundColor Yellow
            } else {
                Write-Host "   ✅ 依存関係インストール完了" -ForegroundColor Green
            }
        } else {
            Write-Host "   ⚠️  requirements.txtが見つかりません" -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "[5] 依存関係のインストールをスキップしました" -ForegroundColor Yellow
    Write-Host "   手動でインストールしてください:" -ForegroundColor Yellow
    Write-Host "   cd $InstallPath" -ForegroundColor Cyan
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Cyan
}

# GPU確認
Write-Host ""
Write-Host "[6] GPU環境の確認..." -ForegroundColor Yellow
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Host "   ✅ NVIDIA GPUが検出されました" -ForegroundColor Green
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | ForEach-Object {
        Write-Host "      $_" -ForegroundColor Gray
    }
} else {
    Write-Host "   ⚠️  NVIDIA GPUが検出されませんでした（CPUモードで動作）" -ForegroundColor Yellow
}

# 完了メッセージ
Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "✅ インストール完了！" -ForegroundColor Green
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""
Write-Host "ComfyUIを起動するには:" -ForegroundColor Cyan
Write-Host "  .\start_comfyui_local.ps1 -ComfyUIPath `"$InstallPath`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "または手動で:" -ForegroundColor Cyan
Write-Host "  cd $InstallPath" -ForegroundColor Yellow
Write-Host "  python main.py --port 8188" -ForegroundColor Yellow
Write-Host ""
Write-Host "ブラウザで http://127.0.0.1:8188 にアクセスしてください" -ForegroundColor Cyan
Write-Host ""


















