# ComfyUI-Managerを一時的に無効化

$managerPath = "C:\ComfyUI\custom_nodes\ComfyUI-Manager"
$backupPath = "C:\ComfyUI\custom_nodes\ComfyUI-Manager.disabled"

Write-Host "============================================================"
Write-Host "ComfyUI-Manager無効化"
Write-Host "============================================================"
Write-Host ""

if (Test-Path $managerPath) {
    if (Test-Path $backupPath) {
        Write-Host "既に無効化されています: $backupPath"
    } else {
        Write-Host "ComfyUI-Managerを無効化中..."
        Rename-Item -Path $managerPath -NewName "ComfyUI-Manager.disabled"
        Write-Host "✅ ComfyUI-Managerを無効化しました"
        Write-Host "   元に戻すには: Rename-Item -Path '$backupPath' -NewName 'ComfyUI-Manager'"
    }
} else {
    Write-Host "ComfyUI-Managerが見つかりません: $managerPath"
    if (Test-Path $backupPath) {
        Write-Host "無効化済みの状態です。"
    }
}

Write-Host ""
Write-Host "ComfyUIを再起動してください。"
