#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Docker Desktopのエラーを診断・修復するスクリプト
    
.DESCRIPTION
    Docker Desktopで発生しているエラーを診断し、自動的に修復を試みます。
    特に以下のエラーに対応:
    - connect ENOENT \\.\pipe\dockerDesktopEngine
    - Failed to fetch extensions
    - Failed to apply settings
#>

$ErrorActionPreference = "Continue"

Write-Host "🔍 Docker Desktop診断・修復スクリプト" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

# ステップ1: Docker CLIの確認
Write-Host "`n[1/6] Docker CLIの確認..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker CLI: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker CLIが見つかりません" -ForegroundColor Red
        Write-Host "💡 Docker Desktopをインストールしてください: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Docker CLIが見つかりません" -ForegroundColor Red
    exit 1
}

# ステップ2: Docker Desktopプロセスの確認
Write-Host "`n[2/6] Docker Desktopプロセスの確認..." -ForegroundColor Yellow
$dockerProcesses = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    Write-Host "✅ Docker Desktopプロセスが実行中です" -ForegroundColor Green
    foreach ($proc in $dockerProcesses) {
        Write-Host "   - PID: $($proc.Id), メモリ: $([math]::Round($proc.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  Docker Desktopプロセスが見つかりません" -ForegroundColor Yellow
    Write-Host "💡 Docker Desktopを起動してください" -ForegroundColor Yellow
}

# ステップ3: Dockerエンジンの接続確認
Write-Host "`n[3/6] Dockerエンジンの接続確認..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dockerエンジンに接続できました" -ForegroundColor Green
        Write-Host "   Dockerエンジンは正常に動作しています" -ForegroundColor Gray
    } else {
        Write-Host "❌ Dockerエンジンに接続できません" -ForegroundColor Red
        Write-Host "   エラー: $($dockerInfo -join '`n')" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Dockerエンジンに接続できません" -ForegroundColor Red
}

# ステップ4: Docker Desktopの再起動
Write-Host "`n[4/6] Docker Desktopの再起動を試みます..." -ForegroundColor Yellow
$restartNeeded = $false

# Docker Desktopプロセスを終了
$dockerProcesses = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    Write-Host "   既存のDocker Desktopプロセスを終了中..." -ForegroundColor Gray
    foreach ($proc in $dockerProcesses) {
        try {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "   ✅ プロセス $($proc.Id) を終了しました" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  プロセス $($proc.Id) の終了に失敗しました" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Seconds 3
    $restartNeeded = $true
}

# Docker Desktopを起動
if ($restartNeeded -or -not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Write-Host "   Docker Desktopを起動中..." -ForegroundColor Gray
    
    # Docker Desktopの実行ファイルパスを検索
    $dockerDesktopPaths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Programs\Docker\Docker\Docker Desktop.exe"
    )
    
    $dockerDesktopExe = $null
    foreach ($path in $dockerDesktopPaths) {
        if (Test-Path $path) {
            $dockerDesktopExe = $path
            break
        }
    }
    
    if ($dockerDesktopExe) {
        try {
            Start-Process -FilePath $dockerDesktopExe -ErrorAction SilentlyContinue
            Write-Host "   ✅ Docker Desktopを起動しました" -ForegroundColor Green
            Write-Host "   ⏳ Dockerエンジンの起動を待機中（最大60秒）..." -ForegroundColor Yellow
            
            # Dockerエンジンの起動を待機
            $maxWait = 60
            $waited = 0
            $dockerReady = $false
            
            while ($waited -lt $maxWait) {
                Start-Sleep -Seconds 2
                $waited += 2
                
                try {
                    $testResult = docker ps 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        $dockerReady = $true
                        break
                    }
                } catch {
                    # 接続エラーは無視して継続
                }
                
                Write-Host "   ." -NoNewline -ForegroundColor Gray
            }
            Write-Host ""
            
            if ($dockerReady) {
                Write-Host "   ✅ Dockerエンジンが起動しました" -ForegroundColor Green
            } else {
                Write-Host "   ⚠️  Dockerエンジンの起動に時間がかかっています" -ForegroundColor Yellow
                Write-Host "   💡 Docker DesktopのGUIで状態を確認してください" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "   ❌ Docker Desktopの起動に失敗しました: $_" -ForegroundColor Red
            Write-Host "   💡 手動でDocker Desktopを起動してください" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  Docker Desktopの実行ファイルが見つかりません" -ForegroundColor Yellow
        Write-Host "   💡 手動でDocker Desktopを起動してください" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ℹ️  Docker Desktopは既に実行中です" -ForegroundColor Cyan
}

# ステップ5: 最終確認
Write-Host "`n[5/6] 最終確認..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dockerエンジンは正常に動作しています" -ForegroundColor Green
        
        # コンテナの状態を確認
        $containers = docker ps -a 2>&1
        if ($LASTEXITCODE -eq 0) {
            $containerCount = ($containers | Measure-Object -Line).Lines - 1
            if ($containerCount -gt 0) {
                Write-Host "   コンテナ数: $containerCount" -ForegroundColor Gray
            } else {
                Write-Host "   コンテナはありません" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "❌ Dockerエンジンにまだ接続できません" -ForegroundColor Red
        Write-Host "   エラー: $($dockerInfo -join '`n')" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Dockerエンジンに接続できません" -ForegroundColor Red
}

# ステップ6: 追加のトラブルシューティング情報
Write-Host "`n[6/6] トラブルシューティング情報..." -ForegroundColor Yellow

# WSL2の状態確認（Windowsの場合）
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    Write-Host "   WSL2の状態を確認中..." -ForegroundColor Gray
    try {
        $wslStatus = wsl --status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ WSL2が利用可能です" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  WSL2の状態を確認できませんでした" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ⚠️  WSL2コマンドが見つかりません" -ForegroundColor Yellow
    }
}

# まとめ
Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "📋 診断結果のまとめ" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

try {
    $finalCheck = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker Desktopは正常に動作しています！" -ForegroundColor Green
        Write-Host "`n💡 次のステップ:" -ForegroundColor Yellow
        Write-Host "   - docker-compose up でコンテナを起動" -ForegroundColor Gray
        Write-Host "   - docker ps でコンテナの状態を確認" -ForegroundColor Gray
    } else {
        Write-Host "❌ Docker Desktopにまだ問題があります" -ForegroundColor Red
        Write-Host "`n💡 推奨される対処法:" -ForegroundColor Yellow
        Write-Host "   1. Docker Desktopを完全に再起動（タスクマネージャーでプロセスを終了）" -ForegroundColor Gray
        Write-Host "   2. Windowsを再起動" -ForegroundColor Gray
        Write-Host "   3. Docker Desktopを再インストール" -ForegroundColor Gray
        Write-Host "   4. WSL2を更新: wsl --update" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Docker Desktopに問題があります" -ForegroundColor Red
}

Write-Host "`n診断完了" -ForegroundColor Cyan
