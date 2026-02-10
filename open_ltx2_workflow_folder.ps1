# LTX-2 example workflow folder - open in Explorer
# Drag LTX-2_I2V_Distilled_wLora.json onto ComfyUI canvas to Load
$folder = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows"
if (Test-Path $folder) {
    explorer $folder
    Write-Host "Opened: $folder"
    Write-Host "Drag LTX-2_I2V_Distilled_wLora.json onto ComfyUI canvas to Load."
} else {
    Write-Host "Folder not found: $folder"
    exit 1
}
