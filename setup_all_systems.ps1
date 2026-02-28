# 全システム統合セットアップスクリプト
# 通知設定、API Gateway起動確認、自動起動設定を一括実行

# Auto-admin check (optional - will continue if admin elevation fails)
. "$PSScriptRoot\common_admin_check.ps1"

Write-Host "=== ManaOS統合システム 全システムセットアップ ===" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 1. 通知設定
Write-Host "[1/5] 通知システム設定..." -ForegroundColor Yellow
Write-Host "既存のSlack設定を確認して統合します" -ForegroundColor Gray
.\setup_notifications.ps1

Write-Host ""
Write-Host "続けますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
$continue = Read-Host
if ($continue -ne "Y" -and $continue -ne "y") {
    Write-Host "セットアップを中断しました" -ForegroundColor Yellow
    exit 0
}

# 2. デバイスAPI Gateway起動確認
Write-Host ""
Write-Host "[2/5] デバイスAPI Gateway起動確認..." -ForegroundColor Yellow

$devices = @(
    @{ Name = "X280"; Endpoint = "http://100.127.121.20:5120/health" }
    @{ Name = "Konoha Server"; Endpoint = "http://100.93.120.33:5106/health" }
    @{ Name = "Pixel 7"; Endpoint = "http://100.127.121.20:5122/health" }
)

foreach ($device in $devices) {
    Write-Host "  $($device.Name) を確認中..." -NoNewline -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $device.Endpoint -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host " [OK]" -ForegroundColor Green
        } else {
            Write-Host " [WARNING: HTTP $($response.StatusCode)]" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " [OFFLINE]" -ForegroundColor Yellow
        Write-Host "    → API Gatewayが起動していない可能性があります" -ForegroundColor Gray
    }
}

# 3. Google Drive認証確認
Write-Host ""
Write-Host "[3/5] Google Drive認証確認..." -ForegroundColor Yellow

$credentialsFile = Join-Path $scriptDir "credentials.json"
$tokenFile = Join-Path $scriptDir "token.json"

if (Test-Path $credentialsFile) {
    Write-Host "  [OK] credentials.jsonが見つかりました" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] credentials.jsonが見つかりません" -ForegroundColor Yellow
    Write-Host "    → Google Drive機能を使用する場合は設定が必要です" -ForegroundColor Gray
}

if (Test-Path $tokenFile) {
    Write-Host "  [OK] token.jsonが見つかりました（認証済み）" -ForegroundColor Green
} else {
    Write-Host "  [INFO] token.jsonが見つかりません（初回認証が必要）" -ForegroundColor Cyan
}

# 4. ADB接続確認（Pixel 7）
Write-Host ""
Write-Host "[4/5] ADB接続確認（Pixel 7）..." -ForegroundColor Yellow

try {
    $adbCheck = adb devices 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pixel7Connected = $adbCheck | Select-String -Pattern "100.127.121.20:5555.*device"
        if ($pixel7Connected) {
            Write-Host "  [OK] Pixel 7に接続されています" -ForegroundColor Green
        } else {
            Write-Host "  [INFO] Pixel 7に接続されていません" -ForegroundColor Cyan
            Write-Host "    → 接続する場合: .\connect_pixel7_adb.ps1" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [WARNING] ADBが見つかりません" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARNING] ADBコマンドの実行エラー" -ForegroundColor Yellow
}

# 5. 自動起動設定（オプション）
Write-Host ""
Write-Host "[5/5] 自動起動設定（オプション）..." -ForegroundColor Yellow
Write-Host "システム起動時に自動的に監視システムを起動しますか？ (Y/N): " -NoNewline -ForegroundColor Yellow
$autostartResponse = Read-Host

if ($autostartResponse -eq "Y" -or $autostartResponse -eq "y") {
    Write-Host "自動起動設定を実行中..." -ForegroundColor Yellow
    
    # 管理者権限チェック
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "[WARNING] 管理者権限が必要です" -ForegroundColor Yellow
        Write-Host "PowerShellを管理者として実行してから再度実行してください" -ForegroundColor Yellow
    } else {
        # タスクスケジューラーに登録
        $taskName = "ManaOS_DeviceMonitoring"
        $scriptPath = Join-Path $scriptDir "start_device_monitoring.ps1"
        
        $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        
        try {
            Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
            Write-Host "[OK] 自動起動設定が完了しました" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] 自動起動設定エラー: $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "自動起動設定をスキップしました" -ForegroundColor Gray
}

# 完了サマリー
Write-Host ""
Write-Host "=== セットアップ完了 ===" -ForegroundColor Green
Write-Host ""
Write-Host "設定された内容:" -ForegroundColor Cyan
Write-Host "  ✅ 通知システム設定"
Write-Host "  ✅ デバイスAPI Gateway確認"
Write-Host "  ✅ Google Drive認証確認"
Write-Host "  ✅ ADB接続確認"
if ($autostartResponse -eq "Y" -or $autostartResponse -eq "y") {
    Write-Host "  ✅ 自動起動設定"
}
Write-Host ""
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "1. 監視システム起動: .\start_device_monitoring.ps1"
Write-Host "2. 全システム起動: .\start_all_enhancements.ps1"
Write-Host "3. 通知が正常に動作するか確認"
Write-Host ""

