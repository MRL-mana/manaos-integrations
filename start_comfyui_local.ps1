# ComfyUI ローカル起動スクリプト（母艦用）
# 新PC（母艦）でComfyUIを起動するためのスクリプト

param(
    [int]$Port = 8188,
    [string]$ComfyUIPath = "",
    [switch]$CPU,
    [switch]$LowVRAM
)

Write-Host "=" -NoNewline
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "ComfyUI ローカル起動スクリプト" -ForegroundColor Cyan
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
        Write-Host "ComfyUIをインストールするか、パスを指定してください:" -ForegroundColor Yellow
        Write-Host "  .\start_comfyui_local.ps1 -ComfyUIPath `"C:\path\to\ComfyUI`"" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "インストール方法:" -ForegroundColor Yellow
        Write-Host "  cd C:\" -ForegroundColor Cyan
        Write-Host "  git clone https://github.com/comfyanonymous/ComfyUI.git" -ForegroundColor Cyan
        Write-Host "  cd ComfyUI" -ForegroundColor Cyan
        Write-Host "  pip install -r requirements.txt" -ForegroundColor Cyan
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
Write-Host "[2] ComfyUIサーバーを起動します..." -ForegroundColor Yellow
Write-Host "   パス: $ComfyUIPath" -ForegroundColor Gray
Write-Host "   ポート: $Port" -ForegroundColor Gray

# ポート使用状況確認
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "   ⚠️  ポート $Port は既に使用中です" -ForegroundColor Yellow
    Write-Host "   使用中のプロセスを終了しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        $processId = $portInUse.OwningProcess
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "   プロセスを終了しました" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host "   起動をキャンセルしました" -ForegroundColor Yellow
        exit 0
    }
}

# 起動引数の構築
$arguments = @("main.py", "--port", $Port.ToString())
if ($CPU) {
    $arguments += "--cpu"
    Write-Host "   CPUモードで起動" -ForegroundColor Gray
}
if ($LowVRAM) {
    $arguments += "--lowvram"
    Write-Host "   低VRAMモードで起動" -ForegroundColor Gray
}

# ComfyUIを起動
Write-Host ""
Write-Host "ComfyUIサーバーを起動中..." -ForegroundColor Green
Write-Host "ブラウザで http://localhost:$Port にアクセスしてください" -ForegroundColor Cyan
Write-Host ""
Write-Host "停止する場合は Ctrl+C を押してください" -ForegroundColor Yellow
Write-Host ""

# ディレクトリを変更してから起動
Push-Location $ComfyUIPath
try {
    python $arguments
} finally {
    Pop-Location
}


















