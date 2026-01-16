# Move models from storage500 to ComfyUI

$SourceDir = "C:\mana_workspace\storage500\civitai_models"
$ComfyUICheckpoints = "C:\ComfyUI\models\checkpoints"
$ComfyUILoras = "C:\ComfyUI\models\loras"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Moving models from storage500 to ComfyUI" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $SourceDir)) {
    Write-Host "Error: Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

$modelFiles = Get-ChildItem -Path $SourceDir -Filter "*.safetensors" -ErrorAction SilentlyContinue

if ($modelFiles.Count -eq 0) {
    Write-Host "No model files found." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found model files: $($modelFiles.Count) files" -ForegroundColor Green
Write-Host ""

$movedCount = 0
$skippedCount = 0
$errorCount = 0

foreach ($file in $modelFiles) {
    # Check if LoRA (contains lora in name or small size)
    $isLora = $file.Name -like "*lora*" -or $file.Name -like "*LoRA*" -or $file.Length -lt 500MB
    
    if ($isLora) {
        $destPath = Join-Path $ComfyUILoras $file.Name
    } else {
        $destPath = Join-Path $ComfyUICheckpoints $file.Name
    }
    
    if (Test-Path $destPath) {
        Write-Host "  [SKIP] $($file.Name) (already exists)" -ForegroundColor Yellow
        $skippedCount++
    } else {
        try {
            Move-Item -Path $file.FullName -Destination $destPath -Force
            $type = if ($isLora) { "LoRA" } else { "Checkpoint" }
            Write-Host "  [MOVE] $($file.Name) -> $type" -ForegroundColor Green
            $movedCount++
        } catch {
            Write-Host "  [ERROR] $($file.Name): $_" -ForegroundColor Red
            $errorCount++
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Move completed" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Moved: $movedCount files" -ForegroundColor Green
Write-Host "Skipped: $skippedCount files" -ForegroundColor Yellow
Write-Host "Errors: $errorCount files" -ForegroundColor Red
Write-Host ""
