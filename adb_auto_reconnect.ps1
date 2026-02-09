# ADB Auto-Reconnect for Pixel 7a over Tailscale
# Runs at PC startup, keeps ADB connection alive
# No WiFi debugging required - uses adb tcpip 5555

$PIXEL_TAILSCALE_IP = "100.84.2.125"
$ADB_PORT = 5555
$PIXEL_USB_SERIAL = "39111JEHN00394"
$CHECK_INTERVAL = 60  # seconds
$LOG_FILE = "$PSScriptRoot\..\logs\adb_auto_reconnect.log"

# Ensure log directory exists
$logDir = Split-Path $LOG_FILE -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line -ErrorAction SilentlyContinue
}

function Test-AdbConnection {
    $devices = adb devices 2>$null | Select-String "${PIXEL_TAILSCALE_IP}:${ADB_PORT}"
    return ($null -ne $devices -and $devices.ToString() -match "device$")
}

function Test-UsbConnection {
    $devices = adb devices 2>$null | Select-String $PIXEL_USB_SERIAL
    return ($null -ne $devices -and $devices.ToString() -match "device$")
}

function Enable-TcpMode {
    # If USB connected, set tcpip mode (survives until reboot)
    if (Test-UsbConnection) {
        Write-Log "USB detected - enabling tcpip mode on port $ADB_PORT"
        $result = adb -s $PIXEL_USB_SERIAL tcpip $ADB_PORT 2>&1
        Write-Log "tcpip result: $result"
        Start-Sleep 3
        return $true
    }
    return $false
}

function Connect-Wireless {
    Write-Log "Attempting wireless ADB connect to ${PIXEL_TAILSCALE_IP}:${ADB_PORT}"
    $result = adb connect "${PIXEL_TAILSCALE_IP}:${ADB_PORT}" 2>&1
    Write-Log "Connect result: $result"
    
    if ($result -match "connected|already") {
        return $true
    }
    return $false
}

Write-Log "=== ADB Auto-Reconnect Started ==="
Write-Log "Pixel 7a Tailscale IP: ${PIXEL_TAILSCALE_IP}:${ADB_PORT}"

# Initial connection attempt
$retryCount = 0
$maxInitRetries = 5

while ($true) {
    try {
        if (Test-AdbConnection) {
            # Already connected wirelessly
            if ($retryCount -gt 0) {
                Write-Log "Reconnected successfully!"
                $retryCount = 0
            }
        }
        else {
            Write-Log "ADB not connected - attempting reconnect..."
            
            # Try 1: Direct wireless connect (if tcpip was already set)
            if (Connect-Wireless) {
                Write-Log "Wireless connection established"
                $retryCount = 0
            }
            # Try 2: USB + tcpip + wireless
            elseif (Enable-TcpMode) {
                Start-Sleep 2
                if (Connect-Wireless) {
                    Write-Log "Re-enabled tcpip via USB + connected wirelessly"
                    $retryCount = 0
                }
            }
            else {
                $retryCount++
                if ($retryCount -le 3) {
                    Write-Log "Connection failed (attempt $retryCount) - Pixel may be rebooting or offline"
                }
                # Suppress repeated logs after 3 failures
            }
        }
    }
    catch {
        Write-Log "Error: $_"
    }
    
    Start-Sleep $CHECK_INTERVAL
}
