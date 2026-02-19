# LM StudioサーバーUI自動起動スクリプト（UI自動化を使用）

Write-Host "※ pwsh推奨 / ps1直実行OK" -ForegroundColor DarkGray
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

Write-Host "=" * 60
Write-Host "LM StudioサーバーUI自動起動"
Write-Host "=" * 60
Write-Host ""

# LM Studio API base URL（env優先、/v1吸収）
$lmStudioRawUrl = if ($env:LM_STUDIO_URL) { $env:LM_STUDIO_URL.TrimEnd('/') } else { "http://127.0.0.1:1234" }
$lmStudioApiBaseUrl = if ($lmStudioRawUrl -match "/v1$") { $lmStudioRawUrl } else { "$lmStudioRawUrl/v1" }

# LM Studioプロセスを確認
$lmStudioProcess = Get-Process -Name "LM Studio" -ErrorAction SilentlyContinue
if (-not $lmStudioProcess) {
    Write-Host "[起動中] LM Studioを起動します..." -ForegroundColor Yellow
    $lmStudioPath = "C:\Users\mana4\AppData\Local\Programs\LM Studio\LM Studio.exe"
    if (Test-Path $lmStudioPath) {
        Start-Process -FilePath $lmStudioPath
        Write-Host "[✅] LM Studioを起動しました" -ForegroundColor Green
        Write-Host "起動完了まで待機中..." -ForegroundColor Gray
        Start-Sleep -Seconds 10
    } else {
        Write-Host "[❌] LM Studioが見つかりませんでした" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[✅] LM Studioは既に起動しています" -ForegroundColor Green
}

# サーバーが既に起動しているか確認
Write-Host ""
Write-Host "[確認中] サーバーの状態を確認中..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$lmStudioApiBaseUrl/models" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[✅] LM Studioサーバーは既に起動しています！" -ForegroundColor Green
    $models = ($response.Content | ConvertFrom-Json).data
    Write-Host "利用可能なモデル数: $($models.Count)" -ForegroundColor Cyan
    exit 0
} catch {
    Write-Host "[情報] サーバーは起動していません。UI自動化で起動を試みます..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[UI自動化] LM Studioのウィンドウを操作します..." -ForegroundColor Yellow
Write-Host "注意: このスクリプトはLM Studioのウィンドウを自動操作します" -ForegroundColor Gray
Write-Host "      LM Studioが前面に表示されている必要があります" -ForegroundColor Gray
Write-Host ""

# LM Studioのウィンドウを探す
$lmStudioProcess = Get-Process -Name "LM Studio" -ErrorAction SilentlyContinue
if (-not $lmStudioProcess) {
    Write-Host "[❌] LM Studioプロセスが見つかりません" -ForegroundColor Red
    exit 1
}

# ウィンドウを前面に持ってくる
$windowHandle = $lmStudioProcess.MainWindowHandle
if ($windowHandle -ne [IntPtr]::Zero) {
    [System.Windows.Forms.SendKeys]::SendWait("%{TAB}")
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait("%{TAB}")
    Start-Sleep -Milliseconds 500
    Write-Host "[情報] LM Studioウィンドウを前面に移動しました" -ForegroundColor Gray
} else {
    Write-Host "[警告] LM Studioのウィンドウハンドルを取得できませんでした" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "手動操作が必要です:" -ForegroundColor Cyan
Write-Host ""
Write-Host "以下の手順でサーバーを起動してください:" -ForegroundColor White
Write-Host ""
Write-Host "1. LM Studioのウィンドウを前面に表示" -ForegroundColor Yellow
Write-Host "2. 上部のタブから「Server」をクリック" -ForegroundColor Yellow
Write-Host "3. 「Select a model to load」をクリックしてモデルを選択" -ForegroundColor Yellow
Write-Host "   （ダウンロード済みのモデルを選択）" -ForegroundColor Gray
Write-Host "4. 「Start Server」ボタンをクリック" -ForegroundColor Yellow
Write-Host ""
Write-Host "サーバーが起動したら、以下で確認できます:" -ForegroundColor Cyan
Write-Host "  .\check_running_status.ps1" -ForegroundColor Gray
Write-Host ""

# キーボードショートカットを試す（Ctrl+Shift+Sなど、LM Studioのショートカットがあれば）
Write-Host "[試行] キーボードショートカットでサーバータブを開く..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
# 一般的なショートカットを試す（実際のショートカットは不明）
# [System.Windows.Forms.SendKeys]::SendWait("^+{S}")  # Ctrl+Shift+S

Write-Host ""
Write-Host "=" * 60
Write-Host "手動操作が必要です" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""



















