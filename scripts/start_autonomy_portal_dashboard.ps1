# Autonomy System + Portal を起動し、自律ダッシュボードをブラウザで開く
# 使い方: .\scripts\start_autonomy_portal_dashboard.ps1
# 注意: Autonomy (5124) と Portal (5108) が未起動であること

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $root) { $root = (Get-Location).Path }
Set-Location $root

$autonomyPort = 5124
$portalPort = 5108
$dashboardUrl = "http://127.0.0.1:$portalPort/autonomy-dashboard"

# 既にポート使用中でないか簡易チェック
$check = Get-NetTCPConnection -LocalPort $autonomyPort -ErrorAction SilentlyContinue
if ($check) {
    Write-Host "Autonomy (${autonomyPort}) は既に使用中の可能性があります。"
}
$check2 = Get-NetTCPConnection -LocalPort $portalPort -ErrorAction SilentlyContinue
if ($check2) {
    Write-Host "Portal (${portalPort}) は既に使用中の可能性があります。"
}

Write-Host "Autonomy System を起動中 (ポート $autonomyPort)..."
Start-Process -FilePath "python" -ArgumentList "autonomy_system.py" -WorkingDirectory $root -WindowStyle Minimized

Start-Sleep -Seconds 2

Write-Host "Portal Integration API を起動中 (ポート $portalPort)..."
Start-Process -FilePath "python" -ArgumentList "portal_integration_api.py" -WorkingDirectory $root -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host "ブラウザでダッシュボードを開きます: $dashboardUrl"
Start-Process $dashboardUrl

Write-Host "完了。Autonomy と Portal は別ウィンドウで動作しています。終了する場合はそれぞれのコンソールで Ctrl+C を押すか、タスクマネージャーで python を終了してください。"
