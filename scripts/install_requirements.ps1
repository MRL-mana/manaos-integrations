# ManaOS 依存パッケージインストールスクリプト（PowerShell）
# 機能別に分割されたrequirementsファイルからインストール

param(
    [string]$Profile = "all",  # all, core, training, voice, comfy, dev
    [switch]$Lock = $false  # requirements.lock.txtを使用するか
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ManaOS 依存パッケージインストール" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# インストールするrequirementsファイルのリスト
$requirements = @()

switch ($Profile) {
    "all" {
        Write-Host "プロファイル: すべて（コア + 学習 + 音声 + ComfyUI）" -ForegroundColor Green
        $requirements = @(
            "requirements-core.txt",
            "requirements-training.txt",
            "requirements-voice.txt",
            "requirements-comfy.txt"
        )
    }
    "core" {
        Write-Host "プロファイル: コアのみ" -ForegroundColor Green
        $requirements = @("requirements-core.txt")
    }
    "training" {
        Write-Host "プロファイル: コア + 学習" -ForegroundColor Green
        $requirements = @(
            "requirements-core.txt",
            "requirements-training.txt"
        )
    }
    "voice" {
        Write-Host "プロファイル: コア + 音声" -ForegroundColor Green
        $requirements = @(
            "requirements-core.txt",
            "requirements-voice.txt"
        )
    }
    "comfy" {
        Write-Host "プロファイル: コア + ComfyUI" -ForegroundColor Green
        $requirements = @(
            "requirements-core.txt",
            "requirements-comfy.txt"
        )
    }
    "dev" {
        Write-Host "プロファイル: コア + 開発環境" -ForegroundColor Green
        $requirements = @(
            "requirements-core.txt",
            "requirements-dev.txt"
        )
    }
    default {
        Write-Host "❌ 不明なプロファイル: $Profile" -ForegroundColor Red
        Write-Host "利用可能なプロファイル: all, core, training, voice, comfy, dev" -ForegroundColor Yellow
        exit 1
    }
}

# ファイルの存在確認
Write-Host ""
Write-Host "[1/3] ファイル確認中..." -ForegroundColor Green
$missingFiles = @()
foreach ($req in $requirements) {
    $path = Join-Path $projectRoot $req
    if (Test-Path $path) {
        Write-Host "  ✅ $req" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $req (見つかりません)" -ForegroundColor Red
        $missingFiles += $req
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ 必要なファイルが見つかりません" -ForegroundColor Red
    exit 1
}

# インストール実行
Write-Host ""
Write-Host "[2/3] 依存パッケージをインストール中..." -ForegroundColor Green

$installCmd = "pip install"
foreach ($req in $requirements) {
    $installCmd += " -r $req"
}

Write-Host "  実行コマンド: $installCmd" -ForegroundColor Cyan
Write-Host ""

try {
    Invoke-Expression $installCmd
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ インストール完了" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ インストールエラー (終了コード: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "❌ インストールエラー: $_" -ForegroundColor Red
    exit 1
}

# インストール確認
Write-Host ""
Write-Host "[3/3] インストール確認中..." -ForegroundColor Green

# 主要パッケージの確認
$keyPackages = @("flask", "torch", "transformers", "requests")
$installed = @()
$missing = @()

foreach ($pkg in $keyPackages) {
    $result = pip show $pkg 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = ($result | Select-String "Version:").ToString().Split(":")[1].Trim()
        Write-Host "  ✅ $pkg ($version)" -ForegroundColor Green
        $installed += $pkg
    } else {
        Write-Host "  ⚠️  $pkg (未インストール)" -ForegroundColor Yellow
        $missing += $pkg
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "インストール完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($missing.Count -gt 0) {
    Write-Host "⚠️  一部のパッケージがインストールされていません" -ForegroundColor Yellow
    Write-Host "   不足しているパッケージ: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  1. 環境変数を設定: scripts\setup_d_drive_env.ps1" -ForegroundColor White
Write-Host "  2. テストを実行: python scripts\test_prompt_optimizer.py" -ForegroundColor White
Write-Host "  3. 学習チェック: python scripts\test_training_checks.py" -ForegroundColor White
Write-Host ""
