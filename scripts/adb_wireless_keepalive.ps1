# ManaOS: ADB Wireless Keepalive (Tailscale)
# Pixel7 (100.84.2.125) への ADB 接続を常時維持する
# - 5555 (tcpip mode) を優先、失敗時は Wireless Debug ポートを自動検出
# - USB接続を検出したら tcpip 5555 を設定して無線に切り替え
# - ログ: %TEMP%\manaos_adb_keepalive.log

$ADB           = "C:\Users\mana4\Desktop\scrcpy\scrcpy-win64-v3.3.4\adb.exe"
$PIXEL7_IP     = "100.84.2.125"
$PIXEL7_PORT   = 5555
$PIXEL7_SERIAL = "39111JEHN00394"  # USB接続時のシリアル
$TARGET        = "${PIXEL7_IP}:${PIXEL7_PORT}"
$LOG           = "$env:TEMP\manaos_adb_keepalive.log"
$INTERVAL      = 30  # 接続チェック間隔（秒）

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LOG -Value $line -Encoding UTF8
    # ログを 500 行以内に保つ
    $lines = Get-Content $LOG -ErrorAction SilentlyContinue
    if ($lines.Count -gt 500) {
        $lines | Select-Object -Last 400 | Set-Content $LOG -Encoding UTF8
    }
}

function Is-WirelessConnected {
    $devices = & $ADB devices 2>&1
    return ($devices -match [regex]::Escape($TARGET) -and $devices -match "device$")
}

function Try-Connect {
    Write-Log "Connecting to $TARGET ..."
    $result = & $ADB connect $TARGET 2>&1
    Write-Log "connect: $result"
    Start-Sleep 2
    return (Is-WirelessConnected)
}

function Setup-TcpIpFromUSB {
    # USB デバイスが device 状態か確認
    $devices = & $ADB devices 2>&1
    if ($devices -match "$PIXEL7_SERIAL\s+device") {
        Write-Log "USB device found. Setting tcpip $PIXEL7_PORT ..."
        & $ADB -s $PIXEL7_SERIAL tcpip $PIXEL7_PORT 2>&1 | ForEach-Object { Write-Log "tcpip: $_" }
        Start-Sleep 3
        return $true
    }
    return $false
}

Write-Log "=== ADB Wireless Keepalive started (target: $TARGET) ==="

# 最初の接続試行
if (-not (Is-WirelessConnected)) {
    # まず直接接続を試みる
    $ok = Try-Connect
    if (-not $ok) {
        # USB接続があれば tcpip 設定してから再接続
        if (Setup-TcpIpFromUSB) {
            $ok = Try-Connect
        }
    }
    if ($ok) { Write-Log "Initial connection OK" }
    else { Write-Log "Initial connection FAILED - will retry" }
} else {
    Write-Log "Already connected to $TARGET"
}

# 常時監視ループ
while ($true) {
    Start-Sleep $INTERVAL

    if (Is-WirelessConnected) {
        # 接続中 - 生存確認 ping
        $ping = Test-Connection -ComputerName $PIXEL7_IP -Count 1 -Quiet -ErrorAction SilentlyContinue
        if (-not $ping) {
            Write-Log "Ping failed - Tailscale may be down"
        }
        # 静かに継続
        continue
    }

    Write-Log "Connection lost. Attempting reconnect..."

    # USB 接続があれば tcpip 設定
    $usbOk = Setup-TcpIpFromUSB

    $ok = Try-Connect
    if ($ok) {
        Write-Log "Reconnected successfully!"
    } else {
        if (-not $usbOk) {
            # USB なし → GTD サーバー経由で Pixel7 に tcpip を有効化させる
            Write-Log "No USB. Calling GTD server /api/adb/reconnect ..."
            try {
                $resp = Invoke-RestMethod -Uri "http://127.0.0.1:5130/api/adb/reconnect" -Method POST -TimeoutSec 10
                Write-Log "GTD reconnect: ok=$($resp.ok) connected=$($resp.connected)"
                Start-Sleep 5
                $ok = Try-Connect
            } catch {
                Write-Log "GTD server unreachable: $_"
            }
        }

        if ($ok) {
            Write-Log "Reconnected successfully (via API)!"
        } else {
            Write-Log "Reconnect failed. Retry in ${INTERVAL}s..."
        }
    }
}
