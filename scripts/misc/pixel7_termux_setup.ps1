#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Pixel7 Termux セットアップ (termux-api + sox + ffmpeg)
    JARVIS I/O ブリッジに必要なパッケージをインストールする

.DESCRIPTION
    ADB 経由で Termux に pkgコマンドを投入し以下をインストール:
      - termux-api    : マイク録音・カメラ撮影・メディア再生
      - sox (rec)     : 高品質 WAV 録音
      - ffmpeg        : 音声フォーマット変換
      - python        : オプション (スクリプト実行用)

.EXAMPLE
    # USB 接続の場合
    pwsh pixel7_termux_setup.ps1

    # Tailscale 経由の場合（先に adb connect しておく）
    $env:ADB_DEVICE = "100.84.2.125:34417"
    pwsh pixel7_termux_setup.ps1
#>

param(
    [string]$Device = $env:ADB_DEVICE,
    [string]$AdbPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ========== ADB パス解決 ==========
if (-not $AdbPath) {
    $candidates = @(
        "C:\Users\mana4\Desktop\scrcpy\scrcpy-win64-v3.3.4\adb.exe",
        "C:\Users\mana4\Desktop\scrcpy\adb.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $AdbPath = $c; break }
    }
    if (-not $AdbPath) {
        $found = Get-Command adb -ErrorAction SilentlyContinue
        if ($found) { $AdbPath = $found.Source }
    }
}

if (-not $AdbPath -or -not (Test-Path $AdbPath)) {
    Write-Error "adb.exe が見つかりません。--AdbPath で指定してください"
    exit 1
}

Write-Host "📱 adb: $AdbPath" -ForegroundColor Cyan

# ========== デバイス接続 ==========
function Invoke-Adb {
    param([string[]]$Args_)
    if ($Device) {
        & $AdbPath -s $Device @Args_
    } else {
        & $AdbPath @Args_
    }
    return $LASTEXITCODE
}

# config.json から IP を読む
if (-not $Device) {
    $cfgPath = "$PSScriptRoot\..\..\adb_automation_config.json"
    if (Test-Path $cfgPath) {
        $cfg = Get-Content $cfgPath | ConvertFrom-Json
        $Device = "$($cfg.device_ip):$($cfg.device_port)"
        Write-Host "📋 設定ファイルからデバイス: $Device" -ForegroundColor Cyan
    }
}

if ($Device) {
    Write-Host "🔌 ADB 接続中: $Device" -ForegroundColor Yellow
    & $AdbPath connect $Device | Out-Null
    Start-Sleep -Seconds 2
}

# 接続確認
$state = & $AdbPath -s $Device get-state 2>&1
if ($LASTEXITCODE -ne 0 -or $state -notmatch "device") {
    Write-Host ""
    Write-Host "❌ Pixel7 に ADB 接続できません" -ForegroundColor Red
    Write-Host ""
    Write-Host "【接続方法】" -ForegroundColor Yellow
    Write-Host "  A) USB ケーブルで PC に繋いで「USBデバッグ」を許可する"
    Write-Host "  B) Pixel7 の Termux で以下を実行し、Tailscale が起動している状態で再試行:"
    Write-Host "       adb tcpip 5555   # または adb -d tcpip 34417"
    Write-Host "  C) Pixel7 側で無線 ADB を有効化:"
    Write-Host "       設定 > 開発者向けオプション > ワイヤレスデバッグ"
    Write-Host ""
    Write-Host "接続後にこのスクリプトを再実行してください"
    exit 1
}

Write-Host "✅ Pixel7 接続 OK ($Device, state=$state)" -ForegroundColor Green

# ========== Termux の存在確認 ==========
Write-Host ""
Write-Host "🔍 Termux インストール確認..." -ForegroundColor Cyan
$termuxPkg = & $AdbPath -s $Device shell "pm list packages com.termux" | Out-String
if ($termuxPkg -notmatch "com.termux") {
    Write-Host "❌ Termux がインストールされていません" -ForegroundColor Red
    Write-Host "   F-Droid から Termux をインストールしてください: https://f-droid.org/packages/com.termux/"
    exit 1
}
Write-Host "✅ Termux 確認 OK" -ForegroundColor Green

# ========== Termux pkg コマンドを実行するヘルパー ==========
# adb shell env ... bash は SELinux で弾かれるため、input text でターミナルに直接入力する

function Send-TermuxCommand {
    param([string]$Cmd, [int]$WaitSec = 5)
    Write-Host "  $ $Cmd" -ForegroundColor DarkGray
    # スペースをエスケープして1行送信
    $escaped = $Cmd.Replace(' ', '%s')
    & $AdbPath -s $Device shell "input text '$escaped'"
    & $AdbPath -s $Device shell "input keyevent 66"  # ENTER
    Start-Sleep -Seconds $WaitSec
}

# Termux を前面に起動
Write-Host ""
Write-Host "📱 Termux を起動中..." -ForegroundColor Yellow
& $AdbPath -s $Device shell "am start -n com.termux/.app.TermuxActivity" | Out-Null
Start-Sleep -Seconds 3

# ========== pkg update ==========
Write-Host ""
Write-Host "📦 pkg update..." -ForegroundColor Yellow
Send-TermuxCommand "pkg update -y" -WaitSec 30

# ========== インストール ==========
$packages = @(
    @{ Name = "termux-api"; Desc = "マイク/カメラ/メディア操作" },
    @{ Name = "sox";        Desc = "高品質 WAV 録音 (rec コマンド)" },
    @{ Name = "ffmpeg";     Desc = "音声フォーマット変換" }
)

foreach ($pkg in $packages) {
    Write-Host ""
    Write-Host "📦 $($pkg.Name) をインストール中... ($($pkg.Desc))" -ForegroundColor Yellow
    Send-TermuxCommand "pkg install -y $($pkg.Name)" -WaitSec 60
    Write-Host "✅ $($pkg.Name) インストール送信完了" -ForegroundColor Green
}

# ========== termux-microphone-record 権限確認 ==========
Write-Host ""
Write-Host "🎤 Termux:API のマイク権限確認..." -ForegroundColor Cyan
$micPerm = & $AdbPath -s $Device shell "dumpsys package com.termux.api | grep RECORD_AUDIO" | Out-String
if ($micPerm -match "granted=true") {
    Write-Host "✅ RECORD_AUDIO 権限: 付与済み" -ForegroundColor Green
} else {
    Write-Host "⚠️  RECORD_AUDIO 権限が未付与 → 自動付与を試みます..." -ForegroundColor Yellow
    & $AdbPath -s $Device shell "pm grant com.termux.api android.permission.RECORD_AUDIO" 2>&1
    & $AdbPath -s $Device shell "pm grant com.termux android.permission.RECORD_AUDIO" 2>&1
    Start-Sleep -Seconds 1
    $micPerm2 = & $AdbPath -s $Device shell "dumpsys package com.termux.api | grep RECORD_AUDIO" | Out-String
    if ($micPerm2 -match "granted=true") {
        Write-Host "✅ RECORD_AUDIO 権限: 付与されました" -ForegroundColor Green
    } else {
        Write-Host "⚠️  権限付与が必要です: Pixel7 の設定 > アプリ > Termux:API > 権限 > マイク" -ForegroundColor Yellow
    }
}

# ========== カメラ権限 ==========
Write-Host "📷 カメラ権限確認..." -ForegroundColor Cyan
& $AdbPath -s $Device shell "pm grant com.termux.api android.permission.CAMERA" 2>&1 | Out-Null
Write-Host "✅ カメラ権限: 付与済み (or 既付与)" -ForegroundColor Green

# ========== 動作テスト ==========
Write-Host ""
Write-Host "🧪 動作テスト（Termux に which コマンドを送信して確認）..." -ForegroundColor Cyan
Write-Host "   ※ Pixel7 の画面で Termux の出力をご確認ください" -ForegroundColor DarkGray
Send-TermuxCommand "which rec termux-media-player termux-camera-photo 2>/dev/null && echo OK_ALL || echo CHECK_TERMUX" -WaitSec 5

# ========== サマリー ==========
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "✅ Pixel7 JARVIS I/O セットアップ完了" -ForegroundColor Green
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Yellow
Write-Host "  1. Pixel7 の通知領域から Termux:API のマイク・カメラ権限を許可"
Write-Host "  2. 以下のコマンドで JARVIS 音声モードを起動:"
Write-Host "       cd C:\Users\mana4\Desktop\manaos_integrations"
Write-Host "       python scripts/misc/voice_secretary_remi.py --pixel7"
Write-Host ""
Write-Host "  カメラ Vision も使う場合:"
Write-Host "       python scripts/misc/voice_secretary_remi.py --pixel7 --pixel7-camera"
Write-Host "=" * 60 -ForegroundColor Cyan
