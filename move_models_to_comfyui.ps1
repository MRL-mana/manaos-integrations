# Downloads folder models to ComfyUI checkpoints directory
# With duplicate check

$ComfyUICheckpoints = "C:\ComfyUI\models\checkpoints"
$DownloadsDir = "$env:USERPROFILE\Downloads"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Moving model files to ComfyUI" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check directories
if (-not (Test-Path $ComfyUICheckpoints)) {
    Write-Host "Error: ComfyUI checkpoints directory not found: $ComfyUICheckpoints" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DownloadsDir)) {
    Write-Host "Error: Downloads directory not found: $DownloadsDir" -ForegroundColor Red
    exit 1
}

# Find model files
$modelFiles = Get-ChildItem -Path $DownloadsDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
$ckptFiles = Get-ChildItem -Path $DownloadsDir -Filter "*.ckpt" -ErrorAction SilentlyContinue
$allFiles = @($modelFiles) + @($ckptFiles)

if ($allFiles.Count -eq 0) {
    Write-Host "No model files found in Downloads folder." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found model files: $($allFiles.Count) files" -ForegroundColor Green
Write-Host ""

$movedCount = 0
$skippedCount = 0
$errorCount = 0

foreach ($file in $allFiles) {
    $destPath = Join-Path $ComfyUICheckpoints $file.Name
    
    if (Test-Path $destPath) {
        Write-Host "  [SKIP] $($file.Name) (already exists)" -ForegroundColor Yellow
        $skippedCount++
    } else {
        try {
            Move-Item -Path $file.FullName -Destination $destPath -Force
            Write-Host "  [MOVE] $($file.Name)" -ForegroundColor Green
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
