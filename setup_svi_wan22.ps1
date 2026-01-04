# SVI × Wan 2.2 セットアップスクリプト
# ComfyUIにSVI × Wan 2.2ワークフローをインストール

param(
    [string]$ComfyUIPath = "",
    [switch]$SkipModelDownload,
    [switch]$SkipCustomNodes
)

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "SVI × Wan 2.2 セットアップスクリプト" -ForegroundColor Cyan
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
        Write-Host "  .\install_comfyui.ps1" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "またはパスを指定してください:" -ForegroundColor Yellow
        Write-Host "  .\setup_svi_wan22.ps1 -ComfyUIPath `"C:\path\to\ComfyUI`"" -ForegroundColor Yellow
        exit 1
    }
    
    $ComfyUIPath = $foundPath
} else {
    if (-not (Test-Path $ComfyUIPath)) {
        Write-Host "❌ 指定されたパスが存在しません: $ComfyUIPath" -ForegroundColor Red
        exit 1
    }
    
    $mainPy = Join-Path $ComfyUIPath "main.py"
    if (-not (Test-Path $mainPy)) {
        Write-Host "❌ main.pyが見つかりません: $ComfyUIPath" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[2] ComfyUI Managerの確認..." -ForegroundColor Yellow
$customNodesPath = Join-Path $ComfyUIPath "custom_nodes"
$managerPath = Join-Path $customNodesPath "ComfyUI-Manager"

if (-not (Test-Path $managerPath)) {
    Write-Host "   ComfyUI Managerをインストール中..." -ForegroundColor Gray
    
    if (-not (Test-Path $customNodesPath)) {
        New-Item -Path $customNodesPath -ItemType Directory -Force | Out-Null
    }
    
    Push-Location $customNodesPath
    try {
        git clone https://github.com/ltdrdata/ComfyUI-Manager.git
        if ($LASTEXITCODE -ne 0) {
            throw "ComfyUI Managerのインストールに失敗しました"
        }
        Write-Host "   ✅ ComfyUI Managerインストール完了" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ エラー: $_" -ForegroundColor Red
        Write-Host "   手動でインストールしてください:" -ForegroundColor Yellow
        Write-Host "   cd $customNodesPath" -ForegroundColor Cyan
        Write-Host "   git clone https://github.com/ltdrdata/ComfyUI-Manager.git" -ForegroundColor Cyan
        Pop-Location
        exit 1
    }
    Pop-Location
} else {
    Write-Host "   ✅ ComfyUI Managerは既にインストールされています" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3] 必要なカスタムノードのインストール..." -ForegroundColor Yellow
Write-Host "   注意: ComfyUIを起動して、ComfyUI Managerから以下をインストールしてください:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   必要なカスタムノード:" -ForegroundColor Cyan
Write-Host "   - ComfyUI-VideoHelperSuite (動画処理)" -ForegroundColor Gray
Write-Host "   - ComfyUI-AnimateDiff-Evolved (動画生成)" -ForegroundColor Gray
Write-Host "   - ComfyUI-Stable-Video-Diffusion (SVI統合)" -ForegroundColor Gray
Write-Host ""
Write-Host "   または、ComfyUI ManagerのUIから「Install Missing Custom Nodes」を実行してください" -ForegroundColor Yellow

if (-not $SkipCustomNodes) {
    Write-Host ""
    Write-Host "   自動インストールを試行しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host "   ⚠️  自動インストールはComfyUI起動後に実行する必要があります" -ForegroundColor Yellow
        Write-Host "   手動でインストールすることを推奨します" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[4] ワークフローテンプレートの配置..." -ForegroundColor Yellow
$workflowsPath = Join-Path $ComfyUIPath "workflows"
if (-not (Test-Path $workflowsPath)) {
    New-Item -Path $workflowsPath -ItemType Directory -Force | Out-Null
}

$templateSource = Join-Path $PSScriptRoot "svi_wan22_workflow_template.json"
$templateDest = Join-Path $workflowsPath "svi_wan22_workflow.json"

if (Test-Path $templateSource) {
    Copy-Item -Path $templateSource -Destination $templateDest -Force
    Write-Host "   ✅ ワークフローテンプレートを配置しました" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  ワークフローテンプレートが見つかりません" -ForegroundColor Yellow
    Write-Host "   後で手動で配置してください" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[5] モデルファイルの確認..." -ForegroundColor Yellow
$modelsPath = Join-Path $ComfyUIPath "models"
$checkpointsPath = Join-Path $modelsPath "checkpoints"

if (-not (Test-Path $checkpointsPath)) {
    New-Item -Path $checkpointsPath -ItemType Directory -Force | Out-Null
}

# Wan 2.2モデルの確認
$wan22Model = Get-ChildItem -Path $checkpointsPath -Filter "*wan*2.2*.safetensors" -ErrorAction SilentlyContinue
if ($wan22Model) {
    Write-Host "   ✅ Wan 2.2モデルが見つかりました: $($wan22Model.Name)" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Wan 2.2モデルが見つかりません" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Wan 2.2モデルをダウンロードする必要があります" -ForegroundColor Yellow
    Write-Host "   モデルのダウンロード先:" -ForegroundColor Cyan
    Write-Host "   - Hugging Face: https://huggingface.co/models" -ForegroundColor Gray
    Write-Host "   - CivitAI: https://civitai.com" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   ダウンロード後、以下のパスに配置してください:" -ForegroundColor Yellow
    Write-Host "   $checkpointsPath" -ForegroundColor Cyan
    
    if (-not $SkipModelDownload) {
        Write-Host ""
        Write-Host "   CivitAI統合を使用してダウンロードしますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq "Y" -or $response -eq "y") {
            Write-Host "   ⚠️  CivitAI統合を使用するには、統合APIサーバーが起動している必要があります" -ForegroundColor Yellow
            Write-Host "   後で手動でダウンロードすることを推奨します" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "[6] 依存関係の確認..." -ForegroundColor Yellow
Push-Location $ComfyUIPath
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   Python: $pythonVersion" -ForegroundColor Gray
    
    # 必要なパッケージの確認
    $requiredPackages = @("torch", "torchvision", "numpy", "pillow")
    $missingPackages = @()
    
    foreach ($package in $requiredPackages) {
        $result = python -c "import $package" 2>&1
        if ($LASTEXITCODE -ne 0) {
            $missingPackages += $package
        }
    }
    
    if ($missingPackages.Count -eq 0) {
        Write-Host "   ✅ 必要なパッケージはインストールされています" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  以下のパッケージが見つかりません: $($missingPackages -join ', ')" -ForegroundColor Yellow
        Write-Host "   インストールしてください:" -ForegroundColor Yellow
        Write-Host "   pip install $($missingPackages -join ' ')" -ForegroundColor Cyan
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "✅ セットアップ完了！" -ForegroundColor Green
Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ComfyUIを起動:" -ForegroundColor Yellow
Write-Host "   .\start_comfyui_local.ps1 -ComfyUIPath `"$ComfyUIPath`"" -ForegroundColor Gray
Write-Host ""
Write-Host "2. ComfyUI Managerでカスタムノードをインストール:" -ForegroundColor Yellow
Write-Host "   - ブラウザで http://localhost:8188 にアクセス" -ForegroundColor Gray
Write-Host "   - 「Manager」ボタンをクリック" -ForegroundColor Gray
Write-Host "   - 「Install Missing Custom Nodes」を実行" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wan 2.2モデルをダウンロード（未ダウンロードの場合）:" -ForegroundColor Yellow
Write-Host "   - モデルを $checkpointsPath に配置" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 動作確認:" -ForegroundColor Yellow
Write-Host "   python test_svi_wan22.py" -ForegroundColor Gray
Write-Host ""

