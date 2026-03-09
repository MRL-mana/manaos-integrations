#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Pixel7 JARVIS 音声秘書レミ 起動スクリプト
    Pixel7 をマイク・スピーカーとして使い、レミと音声で会話する

.DESCRIPTION
    実行内容:
      1. ADB 接続確認
      2. Termux sshd 起動確認（必要なら ADB 経由で起動）
      3. voice_secretary_remi.py --pixel7 を起動

.EXAMPLE
    # 通常起動（マイク+スピーカー）
    pwsh run_pixel7_jarvis.ps1

    # カメラ Vision も有効
    pwsh run_pixel7_jarvis.ps1 -Camera

    # 録音秒数を変更（デフォルト5秒）
    pwsh run_pixel7_jarvis.ps1 -RecordDuration 8
#>

param(
    [switch]$Camera,
    [int]   $RecordDuration = 5,
    [string]$Device = "",
    [switch]$SkipSshdCheck
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# .venv310 (Python 3.10) を優先: so-vits-svc-fork + torch が利用可能
# .venv (Python 3.14) はフォールバック
$Python310 = "$RepoRoot\.venv310\Scripts\python.exe"
$Python314 = "$RepoRoot\.venv\Scripts\python.exe"

if (Test-Path $Python310) {
    $Python = $Python310
    $svcAvail = $true
} elseif (Test-Path $Python314) {
    $Python = $Python314
    $svcAvail = $false
} else {
    $Python = (Get-Command python -ErrorAction SilentlyContinue)?.Source ?? "python"
    $svcAvail = $false
}

# Python 環境確認
if (-not (Test-Path $Python)) {
    # Fallback
    $Python = (Get-Command python -ErrorAction SilentlyContinue)?.Source ?? "python"
}

Write-Host "🐍 Python: $Python" -ForegroundColor Cyan
if ($svcAvail) { Write-Host "🎤 So-VITS-SVC: 使用可能" -ForegroundColor Green }
else           { Write-Host "🎤 So-VITS-SVC: 未使用（.venv310 なし）" -ForegroundColor Yellow }
Write-Host "📁 Repo  : $RepoRoot" -ForegroundColor Cyan

# PYTHONPATH 設定
$env:PYTHONPATH = "$RepoRoot;$RepoRoot\scripts\misc;$RepoRoot\unified_api"

# ========== ADB 接続確認 ==========
$adb = ""
$candidates = @(
    "C:\Users\mana4\Desktop\scrcpy\scrcpy-win64-v3.3.4\adb.exe",
    "C:\Users\mana4\Desktop\scrcpy\adb.exe"
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $adb = $c; break }
}
if (-not $adb) {
    $found = Get-Command adb -ErrorAction SilentlyContinue
    if ($found) { $adb = $found.Source }
}

if ($adb) {
    $cfgPath = "$RepoRoot\adb_automation_config.json"
    if (-not $Device -and (Test-Path $cfgPath)) {
        $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
        $Device = "$($cfg.device_ip):$($cfg.device_port)"
    }

    Write-Host ""
    Write-Host "🔌 ADB 接続確認: $Device" -ForegroundColor Yellow
    & $adb connect $Device 2>&1 | Out-Null
    $state = (& $adb -s $Device get-state 2>&1) -join ""

    if ($state -match "device") {
        Write-Host "✅ ADB 接続 OK" -ForegroundColor Green
    } else {
        Write-Host "⚠️  ADB 接続失敗 ($state) → Pixel7 なしで起動します" -ForegroundColor Yellow
        $Camera = $false
    }
} else {
    Write-Host "⚠️  adb.exe が見つかりません → Pixel7 なしで起動" -ForegroundColor Yellow
}

# ========== sshd 確認 ==========
if (-not $SkipSshdCheck -and $adb -and $state -match "device") {
    Write-Host ""
    Write-Host "🔍 Termux sshd 確認..." -ForegroundColor Yellow

    $cfgPath = "$RepoRoot\adb_automation_config.json"
    $sshPort = 8022
    $sshKey  = "$env:USERPROFILE\.ssh\id_ed25519"
    $sshHost = "100.84.2.125"

    if (Test-Path $cfgPath) {
        $cfg_ssh = Get-Content $cfgPath -Raw | ConvertFrom-Json
        $sshPort = if ($cfg_ssh.ssh_port)     { $cfg_ssh.ssh_port }    else { 8022 }
        $sshHost = if ($cfg_ssh.device_ip)    { $cfg_ssh.device_ip }   else { "100.84.2.125" }
        $rawKey  = if ($cfg_ssh.ssh_key_path) { $cfg_ssh.ssh_key_path } else { "~/.ssh/id_ed25519" }
        $sshKey  = [System.IO.Path]::GetFullPath($rawKey.Replace("~", $env:USERPROFILE))
    }

    $sshTest = & ssh -i $sshKey -p $sshPort -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 $sshHost "echo SSH_OK" 2>&1
    if ($sshTest -match "SSH_OK") {
        Write-Host "✅ sshd 接続 OK (port $sshPort)" -ForegroundColor Green
    } else {
        Write-Host "⏳ sshd 未応答 → ADB 経由で起動..." -ForegroundColor Yellow
        & $adb -s $Device shell "am start -n com.termux/.app.TermuxActivity" 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        & $adb -s $Device shell "input text 'sshd%s-p%s$sshPort'" 2>&1 | Out-Null
        & $adb -s $Device shell "input keyevent 66" 2>&1 | Out-Null
        Start-Sleep -Seconds 5

        $sshTest2 = & ssh -i $sshKey -p $sshPort -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 $sshHost "echo SSH_OK" 2>&1
        if ($sshTest2 -match "SSH_OK") {
            Write-Host "✅ sshd 起動成功" -ForegroundColor Green
        } else {
            Write-Host "⚠️  sshd 起動失敗 → 録音に影響する可能性があります" -ForegroundColor Yellow
        }
    }
}

# ========== voice_secretary_remi.py 起動 ==========
Write-Host ""
Write-Host "🎤 秘書レミ Pixel7 モード起動..." -ForegroundColor Green
Write-Host ""

$args_list = @("scripts/misc/voice_secretary_remi.py", "--pixel7")

if ($Camera) {
    $args_list += "--pixel7-camera"
    Write-Host "  📷 カメラ Vision: 有効" -ForegroundColor Cyan
}

if ($RecordDuration -ne 5) {
    $args_list += "--record-sec"
    $args_list += "$RecordDuration"
}

Write-Host "  コマンド: python $($args_list -join ' ')" -ForegroundColor DarkGray
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  「レミ」と呼びかけると起動します" -ForegroundColor Green
Write-Host "  Ctrl+C で終了" -ForegroundColor DarkGray
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

Set-Location $RepoRoot
& $Python @args_list
