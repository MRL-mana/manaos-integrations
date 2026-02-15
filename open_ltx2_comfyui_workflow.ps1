# ComfyUI をブラウザで開き、LTX-2 例ワークフローのパスをクリップボードにコピー
$comfyUiPort = if ($env:COMFYUI_PORT) { [int]$env:COMFYUI_PORT } else { 8188 }
$comfyUrl = if ($env:COMFYUI_URL) { $env:COMFYUI_URL.TrimEnd('/') } else { "http://127.0.0.1:$comfyUiPort" }
$workflowPath = "C:\ComfyUI\custom_nodes\ComfyUI-LTXVideo\example_workflows\LTX-2_I2V_Distilled_wLora.json"
Start-Process $comfyUrl
Set-Clipboard -Value $workflowPath
Write-Host "ComfyUI opened. Workflow path copied to clipboard:"
Write-Host $workflowPath
Write-Host "Paste in ComfyUI Load dialog or drag the file onto the canvas."
