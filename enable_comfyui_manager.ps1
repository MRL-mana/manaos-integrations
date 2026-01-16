# ComfyUI-Managerを再有効化

$managerPath = "C:\ComfyUI\custom_nodes\ComfyUI-Manager"
$backupPath = "C:\ComfyUI\custom_nodes\ComfyUI-Manager.disabled"

Write-Host "============================================================"
Write-Host "ComfyUI-Manager再有効化"
Write-Host "============================================================"
Write-Host ""

if (Test-Path $backupPath) {
    if (Test-Path $managerPath) {
        Write-Host "既に有効化されています: $managerPath"
    } else {
        Write-Host "ComfyUI-Managerを再有効化中..."
        Rename-Item -Path $backupPath -NewName "ComfyUI-Manager"
        Write-Host "✅ ComfyUI-Managerを再有効化しました"
    }
} else {
    Write-Host "無効化されたComfyUI-Managerが見つかりません: $backupPath"
}

Write-Host ""
Write-Host "ComfyUIを再起動してください。"
