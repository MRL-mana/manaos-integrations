# Move LoRA files from checkpoints to loras directory
# Also move LoRA files from other locations

$ComfyUILoras = "C:\ComfyUI\models\loras"
$ComfyUICheckpoints = "C:\ComfyUI\models\checkpoints"
$DownloadsDir = "$env:USERPROFILE\Downloads"
$DesktopDir = "$env:USERPROFILE\Desktop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Moving LoRA files to ComfyUI loras directory" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check directories
if (-not (Test-Path $ComfyUILoras)) {
    Write-Host "Creating loras directory: $ComfyUILoras" -ForegroundColor Yellow
    New-Item -Path $ComfyUILoras -ItemType Directory -Force | Out-Null
}

# Find LoRA files in checkpoints (shouldn't be there)
$loraInCheckpoints = @()
$loraInCheckpoints += Get-ChildItem -Path $ComfyUICheckpoints -Filter "*lora*.safetensors" -ErrorAction SilentlyContinue
$loraInCheckpoints += Get-ChildItem -Path $ComfyUICheckpoints -Filter "*lora*.ckpt" -ErrorAction SilentlyContinue

# Find LoRA files in Downloads
$loraInDownloads = @()
$loraInDownloads += Get-ChildItem -Path $DownloadsDir -Filter "*lora*.safetensors" -ErrorAction SilentlyContinue
$loraInDownloads += Get-ChildItem -Path $DownloadsDir -Filter "*lora*.ckpt" -ErrorAction SilentlyContinue

# Find LoRA files in Desktop (lora_output directories)
$loraInDesktop = @()
$loraInDesktop += Get-ChildItem -Path $DesktopDir -Recurse -Filter "*.safetensors" -ErrorAction SilentlyContinue -Depth 2 | Where-Object { $_.DirectoryName -like "*lora*" }

$allLoras = @($loraInCheckpoints) + @($loraInDownloads) + @($loraInDesktop)

if ($allLoras.Count -eq 0) {
    Write-Host "No LoRA files found." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found LoRA files: $($allLoras.Count) files" -ForegroundColor Green
Write-Host ""

$movedCount = 0
$skippedCount = 0
$errorCount = 0

foreach ($file in $allLoras) {
    $destPath = Join-Path $ComfyUILoras $file.Name
    
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
