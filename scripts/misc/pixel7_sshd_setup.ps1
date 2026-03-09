#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Pixel7 Termux sshd セットアップ & 起動スクリプト
    PC から Pixel7 の Termux に SSH 接続できるようにする

.DESCRIPTION
    実行内容:
      1. Pixel7 ADB 接続確認
      2. sshd が既に動いているか確認（ポート 8022）
      3. 未起動なら ADB 経由で Termux に sshd 起動コマンドを送信
      4. ~/.termux/boot/start_sshd.sh を配置（Termux:Boot で自動起動）
      5. PC から SSH 接続テスト

.EXAMPLE
    # デフォルト（adb_automation_config.json から IP 読み込み）
    pwsh pixel7_sshd_setup.ps1

    # デバイスを明示指定
    pwsh pixel7_sshd_setup.ps1 -Device "100.84.2.125:5555"

    # SSH キーも明示指定
    pwsh pixel7_sshd_setup.ps1 -SshKeyPath "C:\Users\mana4\.ssh\id_ed25519"
#>

param(
    [string]$Device    = $env:ADB_DEVICE,
    [string]$AdbPath   = "",
    [string]$SshKeyPath = "",
    [int]   $SshPort   = 0,
    [switch]$SkipBoot           # Termux:Boot セットアップをスキップ
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
    Write-Error "adb.exe が見つかりません。-AdbPath で指定してください"
    exit 1
}

# ========== 設定ファイル読み込み ==========
$cfgPath = Join-Path $PSScriptRoot "..\..\adb_automation_config.json"
$cfg = @{}
if (Test-Path $cfgPath) {
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json -AsHashtable
}

if (-not $Device) {
    $ip   = if ($cfg.device_ip)   { $cfg.device_ip }   else { "100.84.2.125" }
    $port = if ($cfg.device_port) { $cfg.device_port } else { 5555 }
    $Device = "${ip}:${port}"
}
if ($SshPort -eq 0) {
    $SshPort = if ($cfg.ssh_port) { [int]$cfg.ssh_port } else { 8022 }
}
if (-not $SshKeyPath) {
    $raw = if ($cfg.ssh_key_path) { $cfg.ssh_key_path } else { "~/.ssh/id_ed25519" }
    $SshKeyPath = [System.IO.Path]::GetFullPath(
        [System.Environment]::ExpandEnvironmentVariables($raw.Replace("~", $env:USERPROFILE))
    )
}

Write-Host "📱 adb    : $AdbPath"    -ForegroundColor Cyan
Write-Host "📱 device : $Device"    -ForegroundColor Cyan
Write-Host "🔑 ssh key: $SshKeyPath" -ForegroundColor Cyan
Write-Host "🔌 port   : $SshPort"   -ForegroundColor Cyan

# ========== ADB 接続 ==========
function Invoke-Adb {
    param([string[]]$Args_)
    & $AdbPath -s $Device @Args_
    return $LASTEXITCODE
}

Write-Host ""
Write-Host "🔌 ADB 接続中: $Device" -ForegroundColor Yellow
& $AdbPath connect $Device 2>&1 | Out-Null
Start-Sleep -Seconds 2

$state = (& $AdbPath -s $Device get-state 2>&1) -join ""
if ($state -notmatch "device") {
    Write-Host "❌ ADB 接続失敗 (state=$state)" -ForegroundColor Red
    Write-Host "   USB またはネットワーク経由で接続してから再実行してください"
    exit 1
}
Write-Host "✅ ADB 接続 OK" -ForegroundColor Green

# ========== sshd 実行確認ヘルパー ==========
function Test-SshdRunning {
    # ポート 8022 が LISTEN しているか確認
    $result = & $AdbPath -s $Device shell "ss -tnlp 2>/dev/null | grep ':$SshPort'" 2>&1
    return ($result -match ":$SshPort")
}

function Test-SshConnection {
    # PC から SSH 接続テスト
    try {
        $r = & ssh -i $SshKeyPath -p $SshPort `
            -o StrictHostKeyChecking=no `
            -o BatchMode=yes `
            -o ConnectTimeout=5 `
            ($cfg.device_ip ?? "100.84.2.125") `
            "echo SSH_OK" 2>&1
        return ($r -match "SSH_OK")
    } catch {
        return $false
    }
}

# ========== Termux コマンド送信ヘルパー ==========
function Send-TermuxCommand {
    param([string]$Cmd, [int]$WaitSec = 3)
    Write-Host "  $ $Cmd" -ForegroundColor DarkGray
    $escaped = $Cmd.Replace(' ', '%s')
    & $AdbPath -s $Device shell "input text '$escaped'" 2>&1 | Out-Null
    & $AdbPath -s $Device shell "input keyevent 66"    2>&1 | Out-Null
    if ($WaitSec -gt 0) { Start-Sleep -Seconds $WaitSec }
}

# ========== Step 1: sshd 起動確認 ==========
Write-Host ""
Write-Host "🔍 sshd 実行状態確認 (port $SshPort)..." -ForegroundColor Yellow

if (Test-SshdRunning) {
    Write-Host "✅ sshd は既に起動中です" -ForegroundColor Green
} else {
    Write-Host "⏳ sshd が未起動 → Termux 経由で起動します..." -ForegroundColor Yellow

    # Termux を前面に起動
    & $AdbPath -s $Device shell "am start -n com.termux/.app.TermuxActivity" 2>&1 | Out-Null
    Start-Sleep -Seconds 3

    # sshd 起動コマンド送信
    Send-TermuxCommand "sshd -p $SshPort" -WaitSec 5

    # 確認
    if (Test-SshdRunning) {
        Write-Host "✅ sshd 起動成功 (port $SshPort)" -ForegroundColor Green
    } else {
        # openssh が未インストールの場合
        Write-Host "⚠️  sshd 未起動 → openssh インストールを試みます..." -ForegroundColor Yellow
        Send-TermuxCommand "pkg install -y openssh" -WaitSec 30
        Send-TermuxCommand "sshd -p $SshPort" -WaitSec 5
        if (Test-SshdRunning) {
            Write-Host "✅ openssh インストール & sshd 起動成功" -ForegroundColor Green
        } else {
            Write-Host "❌ sshd 起動に失敗しました" -ForegroundColor Red
            Write-Host "   Pixel7 の Termux 画面を確認してください"
            exit 1
        }
    }
}

# ========== Step 2: Termux Boot 自動起動スクリプト配置 ==========
if (-not $SkipBoot) {
    Write-Host ""
    Write-Host "🚀 Termux Boot 自動起動スクリプト設定..." -ForegroundColor Yellow

    # Termux:Boot インストール確認
    $termuxBoot = (& $AdbPath -s $Device shell "pm list packages com.termux.boot" 2>&1) -join ""
    if ($termuxBoot -notmatch "com.termux.boot") {
        Write-Host "⚠️  Termux:Boot 未インストール → 自動起動スクリプトはスキップ" -ForegroundColor Yellow
        Write-Host "   F-Droid から com.termux.boot をインストールすると再起動時に sshd が自動起動します"
    } else {
        Write-Host "✅ Termux:Boot 確認 OK" -ForegroundColor Green

        # ブートスクリプト内容を /sdcard に書き出してから Termux でコピー
        $bootScript = @'
#!/data/data/com.termux/files/usr/bin/bash
# Termux Boot: sshd 自動起動
# ~/.termux/boot/start_sshd.sh

# ログ先
LOG="$HOME/.termux/boot_sshd.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] start_sshd.sh 実行" >> "$LOG"

# sshd 起動
if ! pgrep -x sshd > /dev/null 2>&1; then
    sshd -p 8022
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] sshd started (port 8022)" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] sshd already running" >> "$LOG"
fi
'@

        # 一時ファイルに書き出して ADB push
        $tmpScript = [System.IO.Path]::GetTempFileName()
        $bootScript | Set-Content -Path $tmpScript -Encoding ascii -NoNewline
        & $AdbPath -s $Device push $tmpScript "/sdcard/start_sshd.sh" 2>&1 | Out-Null
        Remove-Item $tmpScript -ErrorAction SilentlyContinue

        # Termux 経由でコピー & 権限付与
        & $AdbPath -s $Device shell "am start -n com.termux/.app.TermuxActivity" 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        Send-TermuxCommand "mkdir -p ~/.termux/boot" -WaitSec 2
        Send-TermuxCommand "cp /sdcard/start_sshd.sh ~/.termux/boot/start_sshd.sh" -WaitSec 2
        Send-TermuxCommand "chmod +x ~/.termux/boot/start_sshd.sh" -WaitSec 2

        # 確認
        $bootCheck = (& $AdbPath -s $Device shell "test -x /data/data/com.termux/files/home/.termux/boot/start_sshd.sh && echo EXIST" 2>&1) -join ""
        if ($bootCheck -match "EXIST") {
            Write-Host "✅ Termux Boot スクリプト配置完了" -ForegroundColor Green
        } else {
            Write-Host "⚠️  boot スクリプトの配置を Termux 画面で確認してください" -ForegroundColor Yellow
        }
    }
}

# ========== Step 3: PC からの SSH 接続テスト ==========
Write-Host ""
Write-Host "🔗 PC から SSH 接続テスト..." -ForegroundColor Yellow

if (-not (Test-Path $SshKeyPath)) {
    Write-Host "❌ SSH 秘密鍵が見つかりません: $SshKeyPath" -ForegroundColor Red
    Write-Host "   以下を実行して鍵を生成してください:"
    Write-Host "   ssh-keygen -t ed25519 -f `"$SshKeyPath`" -N ''"
    exit 1
}

$sshHost = if ($cfg.device_ip) { $cfg.device_ip } else { "100.84.2.125" }
if (Test-SshConnection) {
    Write-Host "✅ SSH 接続成功! Pixel7 Termux に SSH で入れます" -ForegroundColor Green
    Write-Host ""
    Write-Host "接続コマンド:" -ForegroundColor Cyan
    Write-Host "  ssh -i `"$SshKeyPath`" -p $SshPort $sshHost" -ForegroundColor White
} else {
    Write-Host "❌ SSH 接続テスト失敗" -ForegroundColor Red
    Write-Host "   確認事項:"
    Write-Host "   - Pixel7 と PC が同じネットワーク（または Tailscale）に接続しているか"
    Write-Host "   - Pixel7 の Termux で authorized_keys が設定されているか:"
    Write-Host "       mkdir -p ~/.ssh"
    Write-Host "       cat /sdcard/authorized_keys >> ~/.ssh/authorized_keys"
    Write-Host "       chmod 600 ~/.ssh/authorized_keys"
    exit 1
}

# ========== サマリー ==========
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "✅ Pixel7 Termux SSH セットアップ完了" -ForegroundColor Green
Write-Host ""
Write-Host "SSH 接続:" -ForegroundColor Yellow
Write-Host "  ssh -i `"$SshKeyPath`" -p $SshPort $sshHost"
Write-Host ""
Write-Host "JARVIS 音声モード起動:" -ForegroundColor Yellow
Write-Host "  cd C:\Users\mana4\Desktop\manaos_integrations"
Write-Host "  python scripts/misc/voice_secretary_remi.py --pixel7"
Write-Host ("=" * 60) -ForegroundColor Cyan
