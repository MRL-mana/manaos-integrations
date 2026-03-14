#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Pixel7 ADB 再起動監視 keepalive スクリプト
  X280 にUSB接続された Pixel7 が再起動 / ADB切断した場合に自動復旧する。

.DESCRIPTION
  1. 30秒おきに adb -s PIXEL7_IP:5555 get-state を確認
  2. 接続切れを検出 → X280 API POST /api/adb/setup を呼ぶ（USB→TCPIP変換）
  3. 母艦側で adb connect PIXEL7_IP:5555 を実行
  4. 復旧を ManaOS notify サーバーへ通知

.NOTES
  タスクスケジューラー登録例:
    Register-ScheduledTask -TaskName "ManaOS_Pixel7_ADB_Keepalive" `
      -Action (New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-NonInteractive -File `"<THIS_FILE>`"") `
      -Trigger (New-ScheduledTaskTrigger -AtStartup) `
      -RunLevel Highest -Force
#>

param(
    [string]$X280Api       = "http://100.127.121.20:5120",
    [string]$Pixel7TcpAddr = "100.127.121.20:5555",   # X280がforward先になるIP:PORT
    [string]$AdbExe        = "C:\Users\mana4\Desktop\scrcpy\scrcpy-win64-v3.3.4\adb.exe",
    [int]   $IntervalSec   = 30,
    [string]$NotifyUrl     = "http://127.0.0.1:5000/api/notify"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"

function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts][$Level] $Msg"
}

function Send-Notify {
    param([string]$Message)
    try {
        $body = @{ message = $Message } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $NotifyUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 | Out-Null
    } catch {
        Write-Log "notify送信失敗: $_" "WARN"
    }
}

function Test-AdbConnection {
    $state = & $AdbExe -s $Pixel7TcpAddr get-state 2>&1
    return ($state -match "device")
}

function Invoke-SetupOnX280 {
    Write-Log "X280 /api/adb/setup を呼び出し中..."
    try {
        $resp = Invoke-RestMethod -Uri "$X280Api/api/adb/setup" -Method Post -TimeoutSec 30
        Write-Log "X280 setup 結果: success=$($resp.success), $($resp.message)"
        return $resp.success
    } catch {
        Write-Log "X280 setup 失敗: $_" "WARN"
        return $false
    }
}

function Connect-AdbPixel7 {
    Write-Log "母艦から adb connect $Pixel7TcpAddr ..."
    $out = & $AdbExe connect $Pixel7TcpAddr 2>&1
    Write-Log "adb connect 結果: $out"
    return ($out -match "connected")
}

# ── メインループ ─────────────────────────────────────────────────────────────
Write-Log "Pixel7 ADB keepalive 開始 (interval=${IntervalSec}s, target=${Pixel7TcpAddr})"

while ($true) {
    if (-not (Test-AdbConnection)) {
        Write-Log "ADB接続切れ検出。復旧を試みます..." "WARN"
        Send-Notify "⚠️ Pixel7 ADB切断検知 — 自動復旧を開始"

        # ① X280 上でUSB→TCPIP変換
        $setupOk = Invoke-SetupOnX280
        if ($setupOk) {
            Start-Sleep -Seconds 3  # TCPIPモード切替の余裕
        } else {
            Write-Log "X280 setup に失敗。次サイクルで再試行します。" "WARN"
            Start-Sleep -Seconds $IntervalSec
            continue
        }

        # ② 母艦側で adb connect
        $connected = Connect-AdbPixel7
        if ($connected) {
            Write-Log "復旧成功 ✅" "INFO"
            Send-Notify "✅ Pixel7 ADB復旧完了 ($Pixel7TcpAddr)"
        } else {
            Write-Log "adb connect 失敗。次サイクルで再試行します。" "WARN"
            Send-Notify "❌ Pixel7 ADB復旧失敗 ($Pixel7TcpAddr) — 次サイクルで再試行"
        }
    }

    Start-Sleep -Seconds $IntervalSec
}
